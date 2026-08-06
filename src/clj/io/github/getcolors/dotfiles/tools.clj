(ns io.github.getcolors.dotfiles.tools
  "Deterministic profile rendering and local installation."
  (:require
   [babashka.fs :as fs]
   [babashka.process :as process]
   [clojure.java.io :as io]
   [clojure.string :as str]
   [io.github.getcolors.dotfiles.utils :as utils]
   [selmer.parser :as selmer]))

(def tool "dotfiles")
(def ^:private resource-root "io/github/getcolors/dotfiles")
(def ^:private executable-paths #{".local/bin/dev"})

(defn- resource-files
  "Discover sorted file paths below a classpath resource directory."
  [dir]
  (let [resource-dir (str resource-root "/" dir)
        url (io/resource resource-dir)
        prefix (str resource-dir "/")]
    (if-not url
      []
      (case (.getProtocol url)
        "file"
        (let [root (io/file url)]
          (->> (file-seq root)
               (filter #(.isFile %))
               (map #(str/replace (str (.relativize (.toPath root) (.toPath %)))
                                  java.io.File/separator "/"))
               sort
               vec))

        "jar"
        (let [connection (.openConnection url)
              entries (enumeration-seq (.entries (.getJarFile connection)))]
          (->> entries
               (remove #(.isDirectory %))
               (map #(.getName %))
               (filter #(str/starts-with? % prefix))
               (map #(subs % (count prefix)))
               (remove str/blank?)
               sort
               vec))

        (throw (ex-info (str "unsupported resource protocol: " (.getProtocol url))
                        {:dir dir :url (str url)}))))))

(defn- profile-resources [profile]
  (let [profile (str profile)
        roots [["common" (resource-files "common")]
               [(str "profiles/" profile)
                (resource-files (str "profiles/" profile))]]
        resources (for [[root paths] roots
                        path paths]
                    {:path path :resource (str resource-root "/" root "/" path)
                     :template? (= root "common")})
        duplicates (->> resources
                        (map :path)
                        frequencies
                        (keep (fn [[path n]] (when (> n 1) path)))
                        sort
                        vec)]
    (when (seq duplicates)
      (throw (ex-info (str "duplicate common/profile dotfiles: "
                           (str/join ", " duplicates))
                      {:profile profile :paths duplicates})))
    (sort-by :path resources)))

(defn profile-files [profile]
  (mapv :path (profile-resources profile)))

(defn tool-dir
  "Resolve generated output beside colors.yml, never relative to the caller."
  [opts]
  (let [workdir (io/file (or (:workdir opts) ".colors"))
        state-dir (when-not (.isAbsolute workdir)
                    (some-> (:green/state-file opts) io/file .getAbsoluteFile .getParent))
        root (if state-dir (io/file state-dir workdir) workdir)]
    (str (io/file root (or (:profile opts) "dotfiles") tool))))

(defn- copy-stream! [input target executable?]
  (let [target (io/file target)]
    (io/make-parents target)
    (with-open [in (io/input-stream input)
                out (io/output-stream target)]
      (io/copy in out))
    (when executable?
      (.setExecutable target true false))
    target))

(defn- render-template! [input target profile executable?]
  (let [target (io/file target)]
    (io/make-parents target)
    (spit target (selmer/render (slurp input) {:profile profile}))
    (when executable?
      (.setExecutable target true false))
    target))

(defn render-step
  "Replace the generated profile tree with common templates and profile files."
  [opts]
  (let [profile (str (:dotfiles-profile opts))
        dir (io/file (tool-dir opts))]
    (when (fs/exists? dir) (fs/delete-tree dir))
    (doseq [{:keys [path resource template?]} (profile-resources profile)]
      (let [resource (io/resource resource)
            target (io/file dir path)
            executable? (contains? executable-paths path)]
        (when-not resource
          (throw (ex-info (str "missing packaged dotfile: " path)
                          {:profile profile :path path})))
        (if template?
          (render-template! resource target profile executable?)
          (copy-stream! resource target executable?))))
    (assoc opts :dotfiles/rendered-dir (str dir))))

(defn install-step
  "Copy only managed files into the target; never remove unrelated home files."
  [opts]
  (let [profile (str (:dotfiles-profile opts))
        source (io/file (or (:dotfiles/rendered-dir opts) (tool-dir opts)))
        target (io/file (utils/expand-home (:dotfiles-target opts)))]
    (doseq [path (profile-files profile)]
      (let [src (io/file source path)
            dst (copy-stream! src (io/file target path)
                              (contains? executable-paths path))]
        (when-not (= -1 (java.nio.file.Files/mismatch (.toPath src) (.toPath dst)))
          (throw (ex-info (str "installed file verification failed: " path)
                          {:path path})))))
    (assoc opts :dotfiles/installed-target (.getCanonicalPath target))))

(defn- color-supported? []
  (zero? (:exit (process/shell {:continue true :out :string :err :string}
                               "diff" "--color=always"
                               "/dev/null" "/dev/null"))))

(def ^:private ansi
  {:reset "\u001b[0m" :bold "\u001b[1m" :cyan "\u001b[36m"
   :red "\u001b[31m" :green "\u001b[32m"})

(defn- line-color [line]
  (cond
    (or (str/starts-with? line "--- ") (str/starts-with? line "+++ ")) :bold
    (str/starts-with? line "@@") :cyan
    (str/starts-with? line "-") :red
    (str/starts-with? line "+") :green))

(defn- print-diff! [text color?]
  (doseq [line (str/split-lines text)]
    (let [color (when color? (line-color line))]
      (if color
        (println (str (get ansi color) line (:reset ansi)))
        (println line)))))

(defn diff-step
  "Print target-to-rendered unified differences without treating drift as an error."
  [opts]
  (let [profile (str (:dotfiles-profile opts))
        rendered (io/file (or (:dotfiles/rendered-dir opts) (tool-dir opts)))
        target (io/file (utils/expand-home (:dotfiles-target opts)))
        color? (color-supported?)
        failures (atom [])]
    (doseq [path (profile-files profile)]
      (let [expected (str (io/file rendered path))
            actual (str (io/file target path))
            {:keys [exit out err]}
            (process/shell {:continue true :out :string :err :string}
                           "diff" "-u" "-N" actual expected)]
        (when (= exit 1)
          (print-diff! out color?))
        ;; diff exits 1 for ordinary differences, including a missing target.
        ;; Only status 2+ is an operational failure.
        (when (> exit 1)
          (when-not (str/blank? err) (binding [*out* *err*] (print err)))
          (swap! failures conj path))))
    (if (seq @failures)
      (assoc opts :green/exit 2
             :green/err (str "diff failed for: "
                             (str/join ", " @failures)))
      (assoc opts :green/exit 0))))

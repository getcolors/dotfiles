(ns io.github.getcolors.dotfiles.tools
  "Deterministic profile rendering and local installation."
  (:require
   [babashka.fs :as fs]
   [babashka.process :as process]
   [clojure.edn :as edn]
   [clojure.java.io :as io]
   [clojure.string :as str]
   [io.github.getcolors.dotfiles.utils :as utils]))

(def tool "dotfiles")
(def ^:private resource-root "io/github/getcolors/dotfiles")
(def ^:private executable-paths #{".local/bin/dev"})

(def manifest
  (delay (-> (str resource-root "/manifest.edn") io/resource slurp edn/read-string)))

(defn profile-files [profile]
  (get @manifest (str profile)))

(defn tool-dir
  "Resolve generated output beside colors.yml, never relative to the caller."
  [opts]
  (let [workdir (io/file (or (:workdir opts) ".colors"))
        state-dir (when-not (.isAbsolute workdir)
                    (some-> (:green/state-file opts) io/file .getAbsoluteFile .getParent))
        root (if state-dir (io/file state-dir workdir) workdir)]
    (str (io/file root (or (:profile opts) "dotfiles") tool))))

(defn- resource-name [profile path]
  (str resource-root "/profiles/" profile "/" path))

(defn- copy-stream! [input target executable?]
  (let [target (io/file target)]
    (io/make-parents target)
    (with-open [in (io/input-stream input)
                out (io/output-stream target)]
      (io/copy in out))
    (when executable?
      (.setExecutable target true false))
    target))

(defn render-step
  "Replace the generated profile tree with an exact copy of packaged resources."
  [opts]
  (let [profile (str (:dotfiles-profile opts))
        dir (io/file (tool-dir opts))]
    (when (fs/exists? dir) (fs/delete-tree dir))
    (doseq [path (profile-files profile)]
      (let [resource (io/resource (resource-name profile path))]
        (when-not resource
          (throw (ex-info (str "missing packaged dotfile: " path)
                          {:profile profile :path path})))
        (copy-stream! resource (io/file dir path)
                      (contains? executable-paths path))))
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

(ns io.github.getcolors.dotfiles.tools
  "Deterministic profile rendering and local installation."
  (:require
   [babashka.fs :as fs]
   [clojure.edn :as edn]
   [clojure.java.io :as io]
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

(ns io.github.getcolors.dotfiles.validate
  "Credential-free desired-state and runtime validation."
  (:require
   [clojure.java.io :as io]
   [clojure.string :as str]
   [green.cli :as green-cli]
   [io.github.getcolors.dotfiles.utils :as utils]))

(def supported-profiles #{"ubuntu" "macos"})
(def profile-par (green-cli/par-name :profile))

(defn placeholder? [x]
  (or (nil? x)
      (and (string? x)
           (or (str/blank? x)
               (= "REPLACE_ME" (str/upper-case x))))))

(defn env-errors
  "Refuse the environment overlay that can redirect generated state."
  [env]
  (when (not-empty (str (get env profile-par)))
    [(str profile-par " is set. Dotfiles takes its profile from colors.yml "
          "only — run from the project directory rather than overriding it.")]))

(defn state-errors
  "Return every desired-state error, rather than stopping at the first."
  [opts]
  (let [target (some-> (:dotfiles-target opts) str utils/expand-home io/file)]
    (vec
     (concat
      (for [k [:profile :workdir :dotfiles-profile :dotfiles-target]
            :when (placeholder? (get opts k))]
        (str k " is required"))
      (when (and (not (placeholder? (:dotfiles-profile opts)))
                 (not (contains? supported-profiles (str (:dotfiles-profile opts)))))
        [(str ":dotfiles-profile must be one of "
              (str/join ", " (sort supported-profiles)))])
      (when-not (boolean? (:dotfiles-prevent-overwrite opts))
        [":dotfiles-prevent-overwrite must be true or false"])
      (when (and target (not (.isAbsolute target)))
        [":dotfiles-target must be ~, begin with ~/, or be an absolute path"])
      (when (and target (= (.getCanonicalPath target) (.getCanonicalPath (io/file "/"))))
        [":dotfiles-target must not be the filesystem root"])))))

(defn runtime-errors
  "Prevent applying an OS-specific profile to the wrong operating system."
  [opts]
  (let [profile (str (:dotfiles-profile opts))
        os (str/lower-case (System/getProperty "os.name" ""))]
    (cond
      (and (= "ubuntu" profile) (not (str/includes? os "linux")))
      ["the ubuntu dotfiles profile can only be created on Linux"]

      (and (= "macos" profile) (not (str/includes? os "mac")))
      ["the macos dotfiles profile can only be created on macOS"]

      :else [])))

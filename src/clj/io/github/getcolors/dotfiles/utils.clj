(ns io.github.getcolors.dotfiles.utils
  "Launcher compatibility and path helpers."
  (:require
   [clojure.java.io :as io]
   [clojure.string :as str]))

(def contract
  "Minimum interface version required by the bundled launcher."
  1)

(defn expand-home
  "Expand an exact ~ or ~/ path without invoking a shell."
  [path]
  (let [path (str path)
        home (System/getProperty "user.home")]
    (cond
      (= "~" path) home
      (str/starts-with? path "~/") (str (io/file home (subs path 2)))
      :else path)))

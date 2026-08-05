(ns pin
  "Stamp the bundled launcher with this repository's clean, pushed HEAD."
  (:require
   [clojure.java.io :as io]
   [clojure.java.shell :as sh]
   [clojure.string :as str]))

(def site
  {:path "skills/package-dotfiles-green/green"
   :rx #"\(def \^:private dotfiles-sha (nil|\"[0-9a-f]{40}\")\)"})

(defn git-out [dir & args]
  (let [{:keys [exit out]} (apply sh/sh "git" "-C" (str dir) args)]
    (when (zero? exit) (str/trim out))))

(defn repo-head [dir]
  (if-let [top (git-out dir "rev-parse" "--show-toplevel")]
    (let [dirty (git-out top "status" "--porcelain")
          sha (git-out top "rev-parse" "HEAD")
          remotes (git-out top "branch" "-r" "--contains" sha)]
      (cond
        (seq dirty) [nil "dotfiles working tree is dirty; commit before pinning"]
        (not (str/includes? (str remotes) "origin/"))
        [nil (str "dotfiles HEAD " (subs sha 0 7) " is not pushed")]
        :else [sha nil]))
    [nil "dotfiles is not a git repository"]))

(defn pin []
  (let [file (io/file (:path site))]
    (if-not (.exists file)
      {:green/exit 2 :green/err (str "pin site is missing: " (:path site))}
      (let [text (slurp file)
            match (re-find (:rx site) text)
            current (second match)
            [head err] (repo-head ".")]
        (cond
          (nil? current) {:green/exit 2 :green/err "could not locate dotfiles-sha"}
          err {:green/exit 2 :green/err err}
          (= current (pr-str head))
          {:green/exit 0 :green/err (str "already pinned to " (subs head 0 7))}
          :else
          (let [matcher (re-matcher (:rx site) text)]
            (.find matcher)
            (spit file (str (subs text 0 (.start matcher 1))
                            (pr-str head)
                            (subs text (.end matcher 1))))
            {:green/exit 0
             :green/err (str "pinned launcher to " (subs head 0 7))}))))))

(let [{:green/keys [exit err]} (pin)]
  (when err (binding [*out* (if (zero? exit) *out* *err*)] (println err)))
  (System/exit exit))

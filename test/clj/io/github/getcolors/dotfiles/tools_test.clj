(ns io.github.getcolors.dotfiles.tools-test
  (:require
   [clojure.java.io :as io]
   [clojure.test :refer [deftest is]]
   [io.github.getcolors.dotfiles.tools :as tools]))

(defn temp-dir []
  (let [f (java.io.File/createTempFile "dotfiles-test-" "")]
    (.delete f)
    (.mkdirs f)
    (str f)))

(deftest manifests-cover-both-profiles-and-no-credentials
  (is (= 17 (count (tools/profile-files "ubuntu"))))
  (is (= 23 (count (tools/profile-files "macos"))))
  (is (not-any? #(or (= ".aws/credentials" %)
                     (= "Library/Application Support/doctl/config.yaml" %))
                (mapcat tools/profile-files ["ubuntu" "macos"]))))

(deftest packaged-profiles-are-fully-rendered
  (doseq [profile ["ubuntu" "macos"]
          path (tools/profile-files profile)
          :let [url (io/resource
                     (str "io/github/getcolors/dotfiles/profiles/"
                          profile "/" path))
                text (when-not (re-find #"\.(png|svg)$" path) (slurp url))]]
    (when text
      (is (not (re-find #"\{[{%]" text))
          (str profile "/" path " contains an unresolved template"))
      (is (not (re-find #"lookup-env" text))
          (str profile "/" path " can materialize an environment secret")))))

(deftest render-is-exact-and-removes-stale-output
  (doseq [profile ["ubuntu" "macos"]]
    (let [workdir (temp-dir)
          opts {:profile (str "render-" profile)
                :workdir workdir
                :dotfiles-profile profile}
          dir (io/file (tools/tool-dir opts))]
      (.mkdirs dir)
      (spit (io/file dir "stale") "stale")
      (let [result (tools/render-step opts)]
        (is (not (.exists (io/file dir "stale"))))
        (is (= (count (tools/profile-files profile))
               (count (filter #(.isFile %) (file-seq dir)))))
        (is (= (str dir) (:dotfiles/rendered-dir result)))
        (is (.canExecute (io/file dir ".local/bin/dev")))))))

(deftest install-copies-and-verifies-managed-files
  (let [workdir (temp-dir)
        target (temp-dir)
        opts {:profile "install-test" :workdir workdir
              :dotfiles-profile "ubuntu" :dotfiles-target target}
        rendered (tools/render-step opts)
        result (tools/install-step rendered)]
    (is (= (.getCanonicalPath (io/file target))
           (:dotfiles/installed-target result)))
    (doseq [path (tools/profile-files "ubuntu")]
      (is (= -1 (java.nio.file.Files/mismatch
                 (.toPath (io/file (:dotfiles/rendered-dir rendered) path))
                 (.toPath (io/file target path))))))))

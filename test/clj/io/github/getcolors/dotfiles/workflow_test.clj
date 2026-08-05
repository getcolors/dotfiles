(ns io.github.getcolors.dotfiles.workflow-test
  (:require
   [clojure.java.io :as io]
   [clojure.string :as str]
   [clojure.test :refer [deftest is]]
   [green.workflow :as wf]
   [io.github.getcolors.dotfiles.validate-test :as vt]
   [io.github.getcolors.dotfiles.workflow :as workflow]))

(defn temp-dir []
  (let [f (java.io.File/createTempFile "dotfiles-workflow-" "")]
    (.delete f)
    (.mkdirs f)
    (str f)))

(defn steps-for [event step]
  (rest (workflow/wire-fn step {:green/event event})))

(deftest build-renders-and-create-installs
  (is (= [:dotfiles/render] (steps-for :build :dotfiles/start)))
  (is (= [] (steps-for :build :dotfiles/render)))
  (is (= [:dotfiles/install] (steps-for :create :dotfiles/render)))
  (is (= [:dotfiles/diff] (steps-for :diff :dotfiles/render))))

(deftest every-side-effect-is-dry-runnable
  (is (= #{:dotfiles/render :dotfiles/install}
         (set workflow/side-effecting-steps))))

(deftest build-diff-and-dry-run-need-no-credentials
  (is (= 0 (:green/exit
            (workflow/start-step (assoc vt/base :green/event :build) {}))))
  (is (= 0 (:green/exit
            (workflow/start-step (assoc vt/base :green/event :diff) {}))))
  (is (= 0 (:green/exit
            (workflow/start-step
             (assoc vt/base :green/event :create :green/dry-run true) {})))))

(deftest real-create-requires-one-run-overwrite-authorization
  (let [guarded (workflow/start-step (assoc vt/base :green/event :create) {})
        allowed (workflow/start-step
                 (assoc vt/base :green/event :create)
                 {"COLORS_PAR_DOTFILES_PREVENT_OVERWRITE" "false"})]
    (is (= 2 (:green/exit guarded)))
    (is (str/includes? (:green/err guarded)
                       "COLORS_PAR_DOTFILES_PREVENT_OVERWRITE=false"))
    (is (= 0 (:green/exit allowed)))))

(deftest profile-overlay-stops-before-rendering
  (let [result (workflow/start-step (assoc vt/base :green/event :build)
                                    {"COLORS_PAR_PROFILE" "other"})]
    (is (= 2 (:green/exit result)))
    (is (str/includes? (:green/err result) "COLORS_PAR_PROFILE"))))

(deftest whole-build-renders-selected-profile
  (let [dir (temp-dir)
        result (wf/run workflow/workflow
                       (assoc vt/base :green/event :build
                              :workdir dir :profile "built"))]
    (is (= 0 (:green/exit result)))
    (is (.exists (io/file dir "built/dotfiles/.gitconfig")))))

(deftest dry-run-touches-nothing
  (let [dir (temp-dir)
        result (wf/run workflow/workflow
                       (assoc vt/base :green/event :create :green/dry-run true
                              :workdir dir :profile "dry"))]
    (is (= 0 (:green/exit result)))
    (is (empty? (seq (.listFiles (io/file dir)))))))

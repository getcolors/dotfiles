(ns io.github.getcolors.dotfiles.validate-test
  (:require
   [clojure.string :as str]
   [clojure.test :refer [deftest is]]
   [io.github.getcolors.dotfiles.validate :as validate]))

(def base
  {:profile "dotfiles-test"
   :workdir ".colors"
   :dotfiles-profile "ubuntu"
   :dotfiles-target "~"
   :dotfiles-prevent-overwrite true})

(deftest complete-state-is-renderable
  (is (= [] (validate/state-errors base))))

(deftest all-required-values-are-reported
  (let [errors (validate/state-errors
                {:dotfiles-prevent-overwrite "true"
                 :dotfiles-target "relative"})
        message (str/join "\n" errors)]
    (doseq [key [":profile" ":workdir" ":dotfiles-profile"]]
      (is (str/includes? message key)))
    (is (str/includes? message ":dotfiles-prevent-overwrite"))
    (is (str/includes? message ":dotfiles-target"))))

(deftest only-packaged-profiles-are-supported
  (is (= #{"ubuntu" "macos"} validate/supported-profiles))
  (is (seq (validate/state-errors (assoc base :dotfiles-profile "windows")))))

(deftest filesystem-root-is-refused
  (is (seq (validate/state-errors (assoc base :dotfiles-target "/")))))

(deftest colors-par-profile-is-refused
  (let [errors (validate/env-errors {"COLORS_PAR_PROFILE" "other"})]
    (is (= 1 (count errors)))
    (is (str/includes? (first errors) "COLORS_PAR_PROFILE")))
  (is (nil? (validate/env-errors {}))))

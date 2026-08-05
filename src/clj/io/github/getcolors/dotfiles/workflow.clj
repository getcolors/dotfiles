(ns io.github.getcolors.dotfiles.workflow
  "The local dotfiles lifecycle DAG. Delete is deliberately unsupported."
  (:require
   [clojure.string :as str]
   [green.cli :as green-cli]
   [green.dry-run :as dry-run]
   [green.progress :as progress]
   [green.workflow :as wf]
   [io.github.getcolors.dotfiles.tools :as tools]
   [io.github.getcolors.dotfiles.validate :as validate]))

(def ^:private defaults
  {:dotfiles-prevent-overwrite true
   :dotfiles-target "~"
   :workdir ".colors"})

(defn start-step
  "Overlay parameters, report every error, and guard a real home overwrite."
  ([opts] (start-step opts (System/getenv)))
  ([opts env]
   (let [opts (green-cli/read-pars (merge defaults opts) env)
         real-create? (and (= :create (:green/event opts))
                           (not (:green/dry-run opts)))
         errors (vec
                 (concat
                  (validate/env-errors env)
                  (validate/state-errors opts)
                  (when real-create? (validate/runtime-errors opts))
                  (when (and real-create? (:dotfiles-prevent-overwrite opts))
                    [(str "dotfile overwrite is protected; set "
                          (green-cli/par-name :dotfiles-prevent-overwrite)
                          "=false for one intentional create")])))]
     (if (seq errors)
       (assoc opts :green/exit 2 :green/err (str/join "\n" errors))
       (assoc opts :green/exit 0)))))

(defn wire-fn [step run-opts]
  (case step
    :dotfiles/start [start-step :dotfiles/render]
    :dotfiles/render (case (:green/event run-opts)
                       :create [tools/render-step :dotfiles/install]
                       :diff [tools/render-step :dotfiles/diff]
                       [tools/render-step])
    :dotfiles/install [tools/install-step]
    :dotfiles/diff [tools/diff-step]))

(def side-effecting-steps [:dotfiles/render :dotfiles/install])

(def workflow
  (-> (wf/workflow {:start :dotfiles/start :wire-fn wire-fn})
      progress/advise
      (dry-run/advise side-effecting-steps)))

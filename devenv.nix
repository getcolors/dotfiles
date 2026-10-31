{ pkgs, ... }:

{
  # Python 3.12 matches CI; uv and Git cover development and the launcher test.
  packages = with pkgs; [ python312 uv git ];
  env.UV_PYTHON = "${pkgs.python312}/bin/python3";
  scripts.dotfiles.exec = ''
    uv run --project "$DEVENV_ROOT" dotfiles "$@"
  '';
}

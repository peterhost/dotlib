# lib/platform.sh — quelle plateforme ? (bash 3.2+, sans lancer aucun processus)
#
#   DOTLIB_OS      darwin | linux | cygwin | msys | other           (d'après $OSTYPE)
#   DOTLIB_FLAVOR  macos | synology | debian | raspbian | osmc | ubuntu | wsl | <ID de os-release>

case ${OSTYPE:-} in
  darwin*) DOTLIB_OS=darwin DOTLIB_FLAVOR=macos ;;
  linux*)  DOTLIB_OS=linux  DOTLIB_FLAVOR=linux ;;
  cygwin*) DOTLIB_OS=cygwin DOTLIB_FLAVOR=cygwin ;;
  msys*)   DOTLIB_OS=msys   DOTLIB_FLAVOR=msys ;;
  *)       DOTLIB_OS=other  DOTLIB_FLAVOR=other ;;
esac

if [ "$DOTLIB_OS" = linux ]; then
  if [ -f /etc/synoinfo.conf ]; then
    DOTLIB_FLAVOR=synology
  elif [ -n "${WSL_DISTRO_NAME:-}" ]; then
    DOTLIB_FLAVOR=wsl
  elif [ -r /etc/os-release ]; then
    while IFS='=' read -r _dotlib_k _dotlib_v; do
      [ "$_dotlib_k" = ID ] || continue
      _dotlib_v=${_dotlib_v#\"}; DOTLIB_FLAVOR=${_dotlib_v%\"}
      break
    done < /etc/os-release
    unset _dotlib_k _dotlib_v
  fi
fi

# lib/hints.sh — outils manquants : quel paquet, quelle commande d'installation
#
# Suppose DOTLIB_OS et DOTLIB_FLAVOR (lib/platform.sh).

dotlib_have() { command -v "$1" >/dev/null 2>&1; }

# Nom du paquet qui fournit une commande, par gestionnaire
dotlib_pkg_of() {
  case $1 in
    rg) echo ripgrep ;;
    gs) echo ghostscript ;;
    fd) case $DOTLIB_FLAVOR in debian|raspbian|osmc|ubuntu) echo fd-find ;; *) echo fd ;; esac ;;
    gls|gdircolors) echo coreutils ;;
    dig) case $DOTLIB_OS in darwin) echo bind ;; *) echo dnsutils ;; esac ;;
    avahi-resolve|avahi-browse) echo avahi-utils ;;      # nmap, arp-scan, fping, nbtscan : même nom
    tput|infocmp|tic) echo ncurses-bin ;;
    # Archives (tools/extract)
    7z|7za) case $DOTLIB_FLAVOR in debian|raspbian|osmc|ubuntu|linuxmint) echo p7zip-full ;; *) echo p7zip ;; esac ;;
    7zz) case $DOTLIB_FLAVOR in debian|raspbian|osmc|ubuntu|linuxmint) echo 7zip ;; *) echo sevenzip ;; esac ;;
    bsdtar) case $DOTLIB_FLAVOR in debian|raspbian|osmc|ubuntu|linuxmint) echo libarchive-tools ;; *) echo libarchive ;; esac ;;
    xz|unxz) case $DOTLIB_FLAVOR in debian|raspbian|osmc|ubuntu|linuxmint) echo xz-utils ;; *) echo xz ;; esac ;;
    unar|lsar) echo unar ;;
    unrar) echo unrar ;;            # apt : dépôt non-free ; brew : retiré du cœur (préférer unar)
    ar) echo binutils ;;
    uncompress) echo ncompress ;;
    bunzip2) echo bzip2 ;;
    gunzip) echo gzip ;;
    *) echo "$1" ;;
  esac
}

# dotlib_install_hint <commande> : commande d'installation adaptée à la machine
dotlib_install_hint() {
  local pkg
  pkg=$(dotlib_pkg_of "$1")
  case $DOTLIB_FLAVOR in
    macos)    echo "brew install $pkg" ;;
    synology) echo "sudo opkg install $pkg" ;;
    debian|raspbian|osmc|ubuntu|linuxmint) echo "sudo apt install $pkg" ;;
    cygwin)   echo "setup-x86_64.exe -q -P $pkg" ;;
    *)        echo "installer le paquet $pkg" ;;
  esac
}

# dotlib_need <commande>… : à appeler dans une fonction ; explique ce qui manque et échoue
dotlib_need() {
  local c missing=0
  for c in "$@"; do
    dotlib_have "$c" && continue
    printf '%s: outil manquant : %s — %s\n' "${FUNCNAME[1]:-dotlib}" "$c" "$(dotlib_install_hint "$c")" >&2
    missing=1
  done
  return $missing
}


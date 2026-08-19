# Bash completion for SyLoPy's run_tests.sh.
#
# Install for the current shell with:
#   source completion/run_tests.bash
#
# To load it automatically, source this file from ~/.bashrc.

_sylo_run_tests_completion() {
    local cur prev script suites
    cur="${COMP_WORDS[COMP_CWORD]}"
    prev="${COMP_WORDS[COMP_CWORD-1]}"
    script="${COMP_WORDS[0]}"

    # Complete suite names from run_tests.sh itself.  This keeps completion
    # synchronized with the authoritative suite list in validate_all_proofs.py.
    if [[ "$prev" == "--suite" ]]; then
        if [[ -x "$script" ]]; then
            suites="$("$script" --list-suites 2>/dev/null | awk '/^[[:space:]]+test/ {print $1}')"
            COMPREPLY=( $(compgen -W "$suites" -- "$cur") )
        fi
        return 0
    fi

    case "$cur" in
        --*)
            COMPREPLY=( $(compgen -W "--suite --verbose --list-suites --help" -- "$cur") )
            ;;
        *)
            # If the previous word is not --suite, complete options.  This
            # also allows: ./run_tests.sh --<TAB>
            COMPREPLY=( $(compgen -W "--suite --verbose --list-suites --help" -- "$cur") )
            ;;
    esac
}

# Bash uses the command word exactly as written here, so register both the
# repository-relative invocation and the bare script name.
complete -F _sylo_run_tests_completion run_tests.sh
complete -F _sylo_run_tests_completion ./run_tests.sh

_awsuser() 
{
    local cur prev opts opts_flags opts_users
    COMPREPLY=()
    cur="${COMP_WORDS[COMP_CWORD]}"
    prev="${COMP_WORDS[COMP_CWORD-1]}"
    # echo "=> $prev --- $cur --> ${COMP_WORDS[@]}"
    opts="create delete reset-console-login search"
    opts_flags="--console-login --console-login --force --verbose"
    # opts_users="`awsuser_completor users`"

    if [[ ${prev} == awsuser ]] ; then
        COMPREPLY=( $(compgen -W "${opts}" ${cur}) )
        return 0
    fi
    if [[ ${cur} == -* ]] ; then
        COMPREPLY=( $(compgen -W "${opts_flags}" -- ${cur}) )
        return 0
    fi
}

# complete -F _awsuser awsuser
# Portable Aurora shell integration. Source this file from an interactive zsh.

# Keep package-manager binaries in stable user-owned locations.
typeset -U path PATH
[[ -d /home/linuxbrew/.linuxbrew/bin ]] && path=(/home/linuxbrew/.linuxbrew/bin $path)
[[ -d /home/linuxbrew/.linuxbrew/sbin ]] && path=(/home/linuxbrew/.linuxbrew/sbin $path)
path=(
  "$HOME/.local/bin"
  "$HOME/.local/share/vixygrey/npm/bin"
  "$HOME/.cargo/bin"
  "$HOME/go/bin"
  $path
)
export PATH
export npm_config_prefix="${npm_config_prefix:-$HOME/.local/share/vixygrey/npm}"
export UV_TOOL_BIN_DIR="${UV_TOOL_BIN_DIR:-$HOME/.local/bin}"
export GOBIN="${GOBIN:-$HOME/.local/bin}"

export BAT_THEME="${BAT_THEME:-Dracula-Sakura}"
export EDITOR="${EDITOR:-micro}"
export VISUAL="${VISUAL:-$EDITOR}"
export FZF_DEFAULT_OPTS="${FZF_DEFAULT_OPTS:---height 45% --layout=reverse --border=rounded --info=inline --prompt=❯\  --pointer=▶ --marker=✓ --color=bg:#282a36,bg+:#323448,fg:#f8f8f2,fg+:#ffffff,hl:#ff9fe3,hl+:#ffc2ec,info:#9be7ff,prompt:#d4b2ff,pointer:#ff9fe3,marker:#8af7cf,spinner:#d4b2ff,header:#8a88c7,border:#d4b2ff,label:#ff9fe3,query:#f8f8f2}"

if command -v vivid >/dev/null 2>&1 && [[ -z "$LS_COLORS" ]]; then
  export LS_COLORS="$(vivid generate dracula)"
fi

if [[ -o interactive && -t 0 && -t 1 ]]; then
  autoload -Uz compinit
  compinit -i -D
  command -v fzf >/dev/null 2>&1 && source <(fzf --zsh)
  command -v direnv >/dev/null 2>&1 && eval "$(direnv hook zsh)"
  command -v mise >/dev/null 2>&1 && eval "$(mise activate zsh)"
  if [[ -z "$AI_AGENT" ]] && command -v assume >/dev/null 2>&1; then
    # Granted must be sourced to update credentials in the user's current shell.
    alias assume='source assume'
  fi
  command -v starship >/dev/null 2>&1 && eval "$(starship init zsh)"
  command -v atuin >/dev/null 2>&1 && eval "$(atuin init zsh)"
  [[ -r /home/linuxbrew/.linuxbrew/share/zsh-autosuggestions/zsh-autosuggestions.zsh ]] &&
    source /home/linuxbrew/.linuxbrew/share/zsh-autosuggestions/zsh-autosuggestions.zsh
  [[ -r /home/linuxbrew/.linuxbrew/share/zsh-syntax-highlighting/zsh-syntax-highlighting.zsh ]] &&
    source /home/linuxbrew/.linuxbrew/share/zsh-syntax-highlighting/zsh-syntax-highlighting.zsh
fi

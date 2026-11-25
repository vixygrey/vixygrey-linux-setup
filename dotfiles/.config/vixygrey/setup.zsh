# Portable Ryoku shell integration. Source this file from an interactive zsh.

# Keep package-manager binaries in stable user-owned locations.
typeset -U path PATH
path=(
  "$HOME/.local/bin"
  "$HOME/.local/share/vixygrey/npm/bin"
  $path
)
export PATH
export npm_config_prefix="${npm_config_prefix:-$HOME/.local/share/vixygrey/npm}"
export UV_TOOL_BIN_DIR="${UV_TOOL_BIN_DIR:-$HOME/.local/bin}"

export BAT_THEME="${BAT_THEME:-Dracula-Sakura}"
export EDITOR="${EDITOR:-hx}"
export VISUAL="${VISUAL:-$EDITOR}"

if command -v vivid >/dev/null 2>&1 && [[ -z "$LS_COLORS" ]]; then
  export LS_COLORS="$(vivid generate dracula)"
fi

if [[ -o interactive && -z "${AI_AGENT:-}" ]]; then
  command -v bat >/dev/null 2>&1 && alias cat='bat --paging=never'
  if command -v eza >/dev/null 2>&1; then
    alias ls='eza --icons'
    alias ll='eza -la --icons --git'
    alias la='eza -a --icons'
    alias lt='eza --tree --icons --level=3'
  fi
  command -v btop >/dev/null 2>&1 && alias top='btop'
  command -v aria2c >/dev/null 2>&1 && alias dl='aria2c'
  command -v yazi >/dev/null 2>&1 && alias y='yazi'
  command -v gping >/dev/null 2>&1 && alias ping='gping'
  command -v doggo >/dev/null 2>&1 && alias dig='doggo'
  command -v procs >/dev/null 2>&1 && alias ps='procs'
  command -v duf >/dev/null 2>&1 && alias df='duf'
fi

if [[ -o interactive && -t 0 && -t 1 ]]; then
  autoload -Uz compinit
  compinit -i -D
  command -v direnv >/dev/null 2>&1 && eval "$(direnv hook zsh)"
  command -v mise >/dev/null 2>&1 && eval "$(mise activate zsh)"
  if [[ -z "$AI_AGENT" ]] && command -v assume >/dev/null 2>&1; then
    # Granted must be sourced to update credentials in the user's current shell.
    alias assume='source assume'
  fi
  command -v starship >/dev/null 2>&1 && eval "$(starship init zsh)"
  [[ -r /usr/share/zsh/plugins/zsh-autosuggestions/zsh-autosuggestions.zsh ]] &&
    source /usr/share/zsh/plugins/zsh-autosuggestions/zsh-autosuggestions.zsh
  if [[ -z "${AI_AGENT:-}" ]]; then
    command -v fzf >/dev/null 2>&1 && source <(fzf --zsh)
    command -v zoxide >/dev/null 2>&1 && eval "$(zoxide init zsh)"
    command -v atuin >/dev/null 2>&1 && eval "$(atuin init zsh)"
  fi
  [[ -r /usr/share/zsh/plugins/zsh-syntax-highlighting/zsh-syntax-highlighting.zsh ]] &&
    source /usr/share/zsh/plugins/zsh-syntax-highlighting/zsh-syntax-highlighting.zsh
fi

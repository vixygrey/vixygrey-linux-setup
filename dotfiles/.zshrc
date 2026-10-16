# Managed Aurora defaults. Put personal shell customizations in a separate file.
[[ -r "${XDG_CONFIG_HOME:-$HOME/.config}/vixygrey/setup.zsh" ]] && source "${XDG_CONFIG_HOME:-$HOME/.config}/vixygrey/setup.zsh"
[[ -r "$HOME/.zshrc.local" ]] && source "$HOME/.zshrc.local"

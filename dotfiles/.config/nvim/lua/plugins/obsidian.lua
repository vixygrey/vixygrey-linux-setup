-- obsidian.nvim: edit Obsidian vaults from Neovim.
-- https://github.com/obsidian-nvim/obsidian.nvim
--
-- No vault path is set here: this setup installs the Obsidian app but never
-- creates or locates a vault for you (see README). Once you have a vault,
-- add it below, e.g.:
--   workspaces = {
--     { name = "personal", path = "~/vaults/personal" },
--   },
-- Without a configured workspace, open Neovim from inside the vault directory.
return {
  "obsidian-nvim/obsidian.nvim",
  version = "*", -- Latest stable release
  ft = "markdown",
  ---@module 'obsidian'
  ---@type obsidian.config
  opts = {
    legacy_commands = false,
    workspaces = {},
  },
}

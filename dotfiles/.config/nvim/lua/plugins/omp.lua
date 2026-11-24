-- omp.nvim: talks to the omp agent running in the current directory.
-- https://github.com/l3aro/omp.nvim
return {
  "l3aro/omp.nvim",
  version = "*", -- Latest stable release
  init = function()
    vim.g.omp_nvim_no_keymaps = true
  end,
  keys = {
    { "<leader>om", "<Cmd>OmpAsk<CR>", desc = "omp: ask" },
    {
      "<leader>om",
      function()
        require("omp_nvim").ask()
      end,
      mode = "x",
      desc = "omp: ask selection",
    },
  },
}

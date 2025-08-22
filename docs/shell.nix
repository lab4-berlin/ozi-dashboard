with (import <nixpkgs> {}); let
  env = bundlerEnv {
    name = "ozi-dashboard-jekyll";
    inherit ruby;
    gemfile = ./Gemfile;
    lockfile = ./Gemfile.lock;
    gemset = ./gemset.nix;
  };
in
  stdenv.mkDerivation {
    name = "ozi-dashboard-jekyll-shell";
    buildInputs = [env ruby];

    shellHook = ''
      echo "Entering Jekyll development shell. Running 'bundle exec jekyll serve'..."
      exec bundle exec jekyll serve # Use exec to keep Jekyll in foreground
    '';
  }
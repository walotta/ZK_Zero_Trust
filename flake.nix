{
    inputs = { nixpkgs.url = "github:NixOS/nixpkgs/nixos-unstable"; };

    outputs = { nixpkgs, ... }:
    let
		pkgs = import nixpkgs {
			config.allowUnfree = true;
			system = "x86_64-linux";
		};
        rzup = pkgs.stdenv.mkDerivation {
            pname = "rzup";
            version = "1.0.0";
            dontUnpack = true;
            dontConfigure = true;
            dontBuild = true;
            installPhase = ''
                install -Dm755 $src $out/bin/rzup
            '';
            src = pkgs.fetchurl {
              url = "https://risc0-artifacts.s3.us-west-2.amazonaws.com/rzup/prod/Linux-X64/rzup";
              hash = "sha256-1p1rK/XLbzcpblZKS7gCUZj7paZ2/N/HgHDIv0hOMms=";
            };
            meta.homepage = "https://github.com/risc0/risc0";
        };
    in {
		devShells.x86_64-linux.default = pkgs.mkShell {
			nativeBuildInputs = with pkgs; [
				rustup
                rzup
                rustc
                llvmPackages.bintools
                python312
				# boost
				# openssl
				# om4
				# llvmPackages.llvm
				# llvmPackages.clang
                gcc
                libgcc
                glibc.dev

                zlib.dev
                xz
                xz.dev
			];
            shellHook = ''
                export PATH="$HOME/.risc0/bin:$PATH"
                export LD_LIBRARY_PATH=${pkgs.zlib}/lib:${pkgs.xz}/lib:$LD_LIBRARY_PATH
                export EXTRA_CCFLAGS="-I/usr/include"
                export CARGO_TARGET_X86_64_UNKNOWN_LINUX_GNU_LINKER=${pkgs.stdenv.cc}/bin/gcc
            '';
		};
    };
}

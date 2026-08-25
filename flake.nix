{
  description = "InkLathe image workshop";

  inputs.nixpkgs.url = "github:NixOS/nixpkgs/nixos-unstable";

  outputs =
    { self, nixpkgs }:
    let
      supportedSystems = [
        "aarch64-linux"
        "x86_64-linux"
      ];
      forAllSystems = nixpkgs.lib.genAttrs supportedSystems;
    in
    {
      packages = forAllSystems (
        system:
        let
          pkgs = nixpkgs.legacyPackages.${system};
          lucidaPython = pkgs.python3.withPackages (
            pythonPackages: with pythonPackages; [
              einops
              huggingface-hub
              kornia
              pillow
              timm
              torch
              torchvision
              transformers
            ]
          );
        in
        {
          default = pkgs.python3Packages.buildPythonApplication {
            pname = "inklathe";
            version = "0.1.0";
            pyproject = true;
            src = ./.;

            build-system = [ pkgs.python3Packages.hatchling ];
            dependencies = with pkgs.python3Packages; [
              fastapi
              pillow
              python-multipart
              uvicorn
            ];

            nativeCheckInputs = with pkgs.python3Packages; [
              httpx
              pytestCheckHook
            ];
            pythonImportsCheck = [ "inklathe" ];

            postInstall = ''
              install -Dm755 scripts/inklathe-engine.sh $out/bin/inklathe-engine
              substituteInPlace $out/bin/inklathe-engine \
                --replace-fail '@PACKAGE_ROOT@' "$out"
              install -Dm644 scripts/engines/common.sh \
                $out/libexec/inklathe/engines/common.sh
              for script in install-realesrgan remove-realesrgan install-lucida remove-lucida; do
                install -Dm755 scripts/engines/$script.sh \
                  $out/libexec/inklathe/engines/$script.sh
              done
              for script in \
                $out/bin/inklathe-engine \
                $out/libexec/inklathe/engines/*.sh; do
                substituteInPlace "$script" \
                  --replace-fail '#!/usr/bin/env bash' '#!${pkgs.bash}/bin/bash'
              done
            '';

            meta = {
              description = "Self-hosted workshop for monochrome artwork";
              homepage = "https://github.com/markstrom/inklathe";
              mainProgram = "inklathe";
            };
          };

          lucida-worker = pkgs.writeShellApplication {
            name = "inklathe-lucida";
            runtimeInputs = [ lucidaPython ];
            text = ''
              exec python ${./scripts/lucida_worker.py} "$@"
            '';
          };
        }
      );

      nixosModules.default = import ./nix/module.nix { inherit self; };
    };
}

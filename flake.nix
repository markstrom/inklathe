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

            meta = {
              description = "Self-hosted workshop for monochrome artwork";
              homepage = "https://github.com/markstrom/inklathe";
              mainProgram = "inklathe";
            };
          };
        }
      );

      nixosModules.default = import ./nix/module.nix { inherit self; };
    };
}

{ self }:
{
  config,
  lib,
  pkgs,
  ...
}:
let
  cfg = config.services.inklathe;
in
{
  options.services.inklathe = {
    enable = lib.mkEnableOption "InkLathe image workshop";

    package = lib.mkOption {
      type = lib.types.package;
      default = self.packages.${pkgs.stdenv.hostPlatform.system}.default;
      defaultText = lib.literalExpression "the package exported by the InkLathe flake";
      description = "InkLathe package to run.";
    };

    domain = lib.mkOption {
      type = lib.types.str;
      default = "inklathe.zerolabs.se";
      description = "Public hostname served by Caddy.";
    };

    port = lib.mkOption {
      type = lib.types.port;
      default = 8787;
      description = "Loopback port used by InkLathe.";
    };

    authUsername = lib.mkOption {
      type = lib.types.str;
      default = "inklathe";
      description = "Username for HTTP Basic authentication.";
    };

    authPasswordFile = lib.mkOption {
      type = lib.types.nullOr lib.types.str;
      default = null;
      example = "/var/lib/secrets/inklathe-auth-password";
      description = ''
        Runtime path to a password file. It is loaded with systemd credentials and is
        intentionally a string rather than a Nix path, preventing secret material from
        being copied into the Nix store.
      '';
    };

    maxDataGB = lib.mkOption {
      type = lib.types.nonnegativeInt;
      default = 20;
      description = "Maximum runtime storage in GiB; zero disables cleanup.";
    };
  };

  config = lib.mkIf cfg.enable {
    assertions = [
      {
        assertion = cfg.authPasswordFile != null;
        message = "services.inklathe.authPasswordFile is required for public access";
      }
    ];

    users.groups.inklathe = { };
    users.users.inklathe = {
      isSystemUser = true;
      group = "inklathe";
      home = "/var/lib/inklathe";
    };

    systemd.tmpfiles.rules = [
      "d /var/lib/inklathe 0750 inklathe inklathe -"
      "d /var/lib/inklathe/textures 0750 inklathe inklathe -"
    ];

    systemd.services.inklathe = {
      description = "InkLathe image workshop";
      wantedBy = [ "multi-user.target" ];
      after = [ "network.target" ];
      environment = {
        INKLATHE_HOST = "127.0.0.1";
        INKLATHE_PORT = toString cfg.port;
        INKLATHE_DATA_DIR = "/var/lib/inklathe";
        INKLATHE_TEXTURE_DIR = "/var/lib/inklathe/textures";
        INKLATHE_MAX_DATA_GB = toString cfg.maxDataGB;
        INKLATHE_AUTH_USERNAME = cfg.authUsername;
      };
      serviceConfig = {
        Type = "simple";
        ExecStart = "${cfg.package}/bin/inklathe";
        User = "inklathe";
        Group = "inklathe";
        LoadCredential = lib.optional (cfg.authPasswordFile != null)
          "inklathe-auth-password:${cfg.authPasswordFile}";
        Restart = "on-failure";
        RestartSec = "5s";
        UMask = "0027";

        NoNewPrivileges = true;
        PrivateTmp = true;
        ProtectHome = true;
        ProtectSystem = "strict";
        ReadWritePaths = [ "/var/lib/inklathe" ];
      };
    };

    services.caddy = {
      enable = true;
      virtualHosts.${cfg.domain}.extraConfig = ''
        encode zstd gzip
        reverse_proxy 127.0.0.1:${toString cfg.port}
      '';
    };

    networking.firewall.allowedTCPPorts = [
      80
      443
    ];
  };
}

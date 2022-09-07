"""Constants for ProxmoxVE."""
import logging

from homeassistant.backports.enum import StrEnum

DOMAIN = "proxmoxve"
UPDATE_INTERVAL = 60
INTEGRATION_NAME = "Proxmox VE"

_LOGGER = logging.getLogger(__package__)

CONF_CONTAINERS = "containers"
CONF_LXC = "lxc"
CONF_NODE = "node"
CONF_NODES = "nodes"
CONF_QEMU = "qemu"
CONF_REALM = "realm"
CONF_VMS = "vms"

DEFAULT_PORT = 8006
DEFAULT_REALM = "pve"
DEFAULT_VERIFY_SSL = False

ID = "vmid"
COORDINATORS = "coordinators"
PROXMOX_CLIENT = "proxmox_client"


class ProxmoxType(StrEnum):
    """Proxmox type of information."""

    Proxmox = "proxmox"
    Node = "node"
    QEMU = "qemu"
    LXC = "lxc"

import uuid
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any, Dict, List


@dataclass
class DeviceConfigTemplate:
    camera_index: int
    image_width: int
    image_height: int
    image_quality: int
    extra_vars: Dict[str, Any] = None


@dataclass
class DeviceSetupResult:
    device_id: str
    config_script: str
    install_commands: List[str]
    environment_vars: Dict[str, str]
    next_steps: List[str]


class PlatformConfigProvider(ABC):
    @abstractmethod
    def get_config_template(self) -> DeviceConfigTemplate:
        pass

    @abstractmethod
    def get_install_commands(self) -> List[str]:
        pass


class RaspberryPiConfigProvider(PlatformConfigProvider):
    def get_config_template(self) -> DeviceConfigTemplate:
        return DeviceConfigTemplate(camera_index=0, image_width=1280, image_height=720, image_quality=80)

    def get_install_commands(self) -> List[str]:
        return [
            "sudo apt update && sudo apt upgrade -y",
            "sudo apt install python3 python3-pip python3-venv git -y",
            "sudo apt install libgl1-mesa-glx libglib2.0-0 -y",
            "python3 -m venv fruit_monitor",
            "source fruit_monitor/bin/activate",
            "pip install --upgrade pip",
            "pip install opencv-python aiohttp Pillow python-dotenv",
            "wget https://raw.githubusercontent.com/your-repo/device_agent.py",
            "chmod +x device_agent.py",
        ]


class LinuxPCConfigProvider(PlatformConfigProvider):
    def get_config_template(self) -> DeviceConfigTemplate:
        return DeviceConfigTemplate(camera_index=0, image_width=1920, image_height=1080, image_quality=85)

    def get_install_commands(self) -> List[str]:
        return [
            "sudo apt update && sudo apt upgrade -y",
            "sudo apt install python3 python3-pip python3-venv git -y",
            "sudo apt install libgl1-mesa-glx libglib2.0-0 -y",
            "python3 -m venv fruit_monitor",
            "source fruit_monitor/bin/activate",
            "pip install --upgrade pip",
            "pip install opencv-python aiohttp Pillow python-dotenv",
            "wget https://raw.githubusercontent.com/your-repo/device_agent.py",
        ]


class WindowsPCConfigProvider(PlatformConfigProvider):
    def get_config_template(self) -> DeviceConfigTemplate:
        return DeviceConfigTemplate(camera_index=0, image_width=1920, image_height=1080, image_quality=90)

    def get_install_commands(self) -> List[str]:
        return [
            "winget install Python.Python.3.11",
            "python -m venv fruit_monitor",
            "fruit_monitor\\Scripts\\activate",
            "python -m pip install --upgrade pip",
            "pip install opencv-python aiohttp Pillow python-dotenv",
            (
                "Invoke-WebRequest -Uri 'https://raw.githubusercontent.com/your-repo/device_agent.py' "
                "-OutFile 'device_agent.py'"
            ),
        ]


class DeviceConfigService:
    def __init__(self):
        self._providers = {
            "raspberry-pi": RaspberryPiConfigProvider(),
            "linux-pc": LinuxPCConfigProvider(),
            "windows-pc": WindowsPCConfigProvider(),
        }

    def generate_device_config(
        self,
        device_name: str,
        location: str,
        device_type: str,
        capture_interval: int,
        api_base_url: str = "https://your-api-gateway-url.com",
    ) -> DeviceSetupResult:

        device_id = f"dev-{uuid.uuid4().hex[:12]}"
        provider = self._providers.get(device_type)

        if not provider:
            provider = LinuxPCConfigProvider()

        template = provider.get_config_template()
        install_commands = provider.get_install_commands()

        env_config = self._generate_env_config(
            device_id, device_name, location, template, capture_interval, api_base_url
        )

        return DeviceSetupResult(
            device_id=device_id,
            config_script=env_config,
            install_commands=install_commands,
            environment_vars={
                "DEVICE_ID": device_id,
                "DEVICE_NAME": device_name,
                "DEVICE_LOCATION": location,
            },
            next_steps=[
                "Salve a configuração como 'config.env'",
                "Execute o script de instalação",
                "Inicie o device_agent.py com a configuração",
                "Verifique se o dispositivo aparece online no dashboard",
            ],
        )

    def _generate_env_config(
        self,
        device_id: str,
        device_name: str,
        location: str,
        template: DeviceConfigTemplate,
        capture_interval: int,
        api_base_url: str,
    ) -> str:
        return f"""# Device Configuration
DEVICE_ID={device_id}
DEVICE_NAME={device_name}
DEVICE_LOCATION={location}

# API Configuration
API_BASE_URL={api_base_url}
AUTO_UPLOAD=true

# Camera Configuration
CAMERA_INDEX={template.camera_index}
CAPTURE_INTERVAL={capture_interval}
IMAGE_QUALITY={template.image_quality}
IMAGE_WIDTH={template.image_width}
IMAGE_HEIGHT={template.image_height}

# Processing Configuration
MATURATION_THRESHOLD=0.6

# Storage Configuration
STORE_LOCAL=true
LOCAL_STORAGE=./captures

# Network Configuration
MAX_RETRIES=3
RETRY_DELAY=10
HEARTBEAT_INTERVAL=60

# Logging Configuration
LOG_LEVEL=INFO
"""

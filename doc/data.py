from typing import Dict, List, Optional, Union
from pathlib import Path
from os import environ
from dataclasses import dataclass
from yaml import safe_load
from tabulate import tabulate


ROOT = Path(__file__).resolve().parent
DOCS_OFFLINE = environ.get("OFL_DOCS_OFFLINE") == "1"
CONSTRAINTS_BASE_URL = "https://hdl.github.io/constraints/boards"


@dataclass
class Board:
    ID: str
    Description: Optional[str] = None
    URL: Optional[str] = None
    FPGA: Optional[str] = None
    Memory: Optional[str] = None
    Flash: Optional[str] = None
    Constraints: Optional[Union[str, List[str]]] = None
    SPIFlash: Optional[str] = None


def ReadBoardDataFromYAML() -> List[Board]:
    with (ROOT / 'boards.yml').open('r', encoding='utf-8') as fptr:
        data = [Board(**item) for item in safe_load(fptr)]
    return data


def BoardDataToTable(data: List[Board], tablefmt: str = "rst") -> str:
    def processConstraints(constraints: Optional[Union[str, List[str]]]) -> Optional[str]:
        if constraints is None:
            return None
        if isinstance(constraints, str):
            constraints = [constraints]
        if DOCS_OFFLINE:
            return " ".join([f"`{item} ➚ <{CONSTRAINTS_BASE_URL}/{item.lower()}.html>`__" for item in constraints])
        return " ".join([f":ref:`{item} ➚ <constraints:boards:{item.lower()}>`" for item in constraints])

    return tabulate(
        [
            [
                item.ID,
                f"`{item.Description} <{item.URL}>`__",
                item.FPGA,
                item.Memory,
                item.Flash,
                item.SPIFlash,
                processConstraints(item.Constraints)
            ] for item in data
        ],
        headers=["Board name", "Description", "FPGA", "Memory", "Flash", "SPI Flash", "Constraints"],
        tablefmt=tablefmt
    )


@dataclass
class FPGA:
    Model: Union[str, List[str]]
    Description: str
    URL: Optional[str] = None
    Memory: Optional[str] = None
    Flash: Optional[str] = None


def ReadFPGADataFromYAML() -> Dict[str, List[FPGA]]:
    with (ROOT / 'FPGAs.yml').open('r', encoding='utf-8') as fptr:
        data = safe_load(fptr)
        for vendor, content in data.items():
            data[vendor] = [FPGA(**item) for item in content]
    return data


def FPGADataToTable(data: Dict[str, List[FPGA]], tablefmt: str = "rst") -> str:
    return tabulate(
        [
            [
                f":ref:`{vendor} <{vendor.lower().replace(' ','')}>`",
                f"`{item.Description} <{item.URL}>`__",
                item.Model if isinstance(item.Model, str) else ', '.join(item.Model),
                item.Memory,
                item.Flash
            ] for vendor, content in data.items() for item in content
        ],
        headers=["Vendor", "Description", "Model", "Memory", "Flash"],
        tablefmt=tablefmt
    )


@dataclass
class Cable:
    Name: str
    Description: str
    URL: Optional[str] = None
    Note: Optional[str] = None


def ReadCableDataFromYAML() -> Dict[str, List[Cable]]:
    with (ROOT / 'cable.yml').open('r', encoding='utf-8') as fptr:
        data = safe_load(fptr)
        for keyword, content in data.items():
            data[keyword] = [Cable(**item) for item in content]
    return data


def CableDataToTable(data: Dict[str, List[Cable]], tablefmt: str = "rst") -> str:
    def processURL(name: str, url: Optional[str]) -> str:
        if url is None:
            return f"{name}"
        else:
            return f"`{name} <{url}>`__"
    return tabulate(
        [
            [
                f"{vendor}",
                processURL(item.Name, item.URL),
                item.Description,
                item.Note
            ] for vendor, content in data.items() for item in content
        ],
        headers=["keyword", "Name", "Description", "Note"],
        tablefmt=tablefmt
    )

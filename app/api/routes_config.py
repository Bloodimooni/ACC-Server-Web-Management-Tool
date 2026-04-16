from typing import Literal

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, Field, model_validator

from app.auth.dependencies import require_auth
from app.api.config_io import read_cfg, write_cfg, cfg_exists

router = APIRouter(prefix="/api/config", dependencies=[Depends(require_auth)])


# ---------------------------------------------------------------------------
# Pydantic models — validated before any disk write
# ---------------------------------------------------------------------------

class ConfigurationModel(BaseModel):
    udpPort: int = Field(ge=1024, le=65535)
    tcpPort: int = Field(ge=1024, le=65535)
    maxConnections: int = Field(ge=1, le=200)
    lanDiscovery: int = Field(ge=0, le=1)
    registerToLobby: int = Field(ge=0, le=1)
    configVersion: int = 1


class SettingsModel(BaseModel):
    serverName: str = Field(max_length=50)
    adminPassword: str
    carGroup: Literal["FreeForAll", "GT3", "GT4", "Cup", "ST", "CHL", "TCX"]
    trackMedalsRequirement: int = Field(ge=-1, le=3)
    safetyRatingRequirement: int = Field(ge=-1, le=99)
    racecraftRatingRequirement: int = Field(ge=-1, le=99)
    password: str
    spectatorPassword: str
    maxCarSlots: int = Field(ge=1, le=60)
    allowAutoDQ: int = Field(ge=0, le=1)
    dumpLeaderboards: int = Field(default=0, ge=0, le=1)
    isRaceLocked: int = Field(default=0, ge=0, le=1)
    shortFormationLap: int = Field(default=0, ge=0, le=1)
    formationLapType: int = Field(default=3, ge=0, le=5)
    doDriverSwapBroadcast: int = Field(default=0, ge=0, le=1)
    latencyStrategy: int = Field(default=0, ge=0, le=1)
    centralEntryListPath: str = ""


class SessionModel(BaseModel):
    hourOfDay: int = Field(ge=0, le=23)
    dayOfWeekend: int = Field(ge=1, le=3)
    timeMultiplier: int = Field(ge=1, le=50)
    sessionType: Literal["P", "Q", "R"]
    sessionDurationMinutes: int = Field(ge=1)


VALID_TRACKS = {
    "barcelona", "brands_hatch", "donington", "hockenheim", "hungaroring",
    "imola", "indianapolis", "kyalami", "laguna_seca", "misano", "monza",
    "mount_panorama", "nordschleife", "nurburgring", "nurburgring_24h",
    "oulton_park", "paul_ricard", "red_bull_ring", "silverstone", "snetterton",
    "spa", "suzuka", "valencia", "watkins_glen", "zandvoort", "zolder",
}


class EventModel(BaseModel):
    track: str
    preRaceWaitingTimeSeconds: int = Field(ge=0)
    sessionOverTimeSeconds: int = Field(ge=0)
    ambientTemp: int = Field(ge=0, le=50)
    cloudLevel: float = Field(ge=0.0, le=1.0)
    rain: float = Field(ge=0.0, le=1.0)
    weatherRandomness: int = Field(ge=0, le=7)
    sessions: list[SessionModel] = Field(min_length=1)
    configVersion: int = 1

    @model_validator(mode="after")
    def validate_track(self):
        if self.track not in VALID_TRACKS:
            raise ValueError(f"Unknown track: {self.track}")
        return self


class EventRulesModel(BaseModel):
    qualifyStandingType: int = Field(ge=1, le=2)
    pitWindowLengthSec: int  # -1 = disabled
    driverStintTimeSec: int  # -1 = disabled
    mandatoryPitstopCount: int = Field(ge=0)
    maxTotalDrivingTime: int  # -1 = disabled
    maxDriversCount: int = Field(ge=1, le=2)
    isRefuellingAllowedInRace: bool
    isRefuellingTimeFixed: bool
    isMandatoryPitstopRefuellingRequired: bool
    isMandatoryPitstopTyreChangeRequired: bool
    isMandatoryPitstopSwapDriverRequired: bool
    tyreSetCount: int = Field(ge=1, le=50)


class AssistRulesModel(BaseModel):
    disableIdealLine: int = Field(ge=0, le=1)
    disableAutosteer: int = Field(ge=0, le=1)
    stabilityControlLevelMax: int = Field(ge=0, le=100)
    disableAutoPitLimiter: int = Field(ge=0, le=1)
    disableAutoGear: int = Field(ge=0, le=1)
    disableAutoClutch: int = Field(ge=0, le=1)
    disableAutoEngineStart: int = Field(ge=0, le=1)
    disableAutoWiper: int = Field(ge=0, le=1)
    disableAutoLights: int = Field(ge=0, le=1)


_MODELS = {
    "configuration": ConfigurationModel,
    "settings": SettingsModel,
    "event": EventModel,
    "eventRules": EventRulesModel,
    "assistRules": AssistRulesModel,
}

# eventRules.json may not exist on a fresh install (only cfg/current/eventRules.txt does).
# Return these defaults so the UI can display and then create the file on first save.
_EVENT_RULES_DEFAULTS = {
    "qualifyStandingType": 1,
    "pitWindowLengthSec": -1,
    "driverStintTimeSec": -1,
    "mandatoryPitstopCount": 0,
    "maxTotalDrivingTime": -1,
    "maxDriversCount": 1,
    "isRefuellingAllowedInRace": True,
    "isRefuellingTimeFixed": False,
    "isMandatoryPitstopRefuellingRequired": False,
    "isMandatoryPitstopTyreChangeRequired": False,
    "isMandatoryPitstopSwapDriverRequired": False,
    "tyreSetCount": 50,
}


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------

@router.get("/{name}")
async def get_config(name: str):
    if name not in _MODELS:
        raise HTTPException(404, "Unknown config name")
    try:
        return read_cfg(name)
    except FileNotFoundError:
        # eventRules.json is not created by the installer — return defaults
        if name == "eventRules":
            return _EVENT_RULES_DEFAULTS
        raise HTTPException(404, f"{name}.json not found in server/cfg/")
    except Exception as exc:
        raise HTTPException(500, f"Failed to read config: {exc}")


@router.post("/{name}")
async def save_config(name: str, request: Request):
    if name not in _MODELS:
        raise HTTPException(404, "Unknown config name")

    try:
        body = await request.json()
    except Exception:
        raise HTTPException(400, "Invalid JSON body")

    model_class = _MODELS[name]
    try:
        validated = model_class.model_validate(body)
    except Exception as exc:
        raise HTTPException(422, str(exc))

    try:
        write_cfg(name, validated.model_dump())
    except Exception as exc:
        raise HTTPException(500, f"Failed to write config: {exc}")

    return {"status": "ok", "config": name}

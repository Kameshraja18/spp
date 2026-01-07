"""Advanced API endpoints for batch predictions, forecasting, alerts, and drift detection."""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field
from typing import List, Optional, Literal
from datetime import datetime, timedelta
import numpy as np

from services.api.schemas import (
    RiskPredictionRequest,
    RiskPredictionResponse,
    SeverityPredictionRequest,
    SeverityPredictionResponse,
)
from services.models.inference import predict_risk, predict_severity
from services.monitoring.metrics import track_prediction_latency

router = APIRouter(prefix="/api/v2", tags=["advanced"])


# ============== GLOBAL COUNTRY INDICATORS (DEMO) ==============


class CountryIndicator(BaseModel):
    """Country-level indicator snapshot (static WHO/observatory values)."""
    country_code: str
    country_name: str
    deaths_per_100k: Optional[float] = None
    helmet_law: Optional[bool] = None
    seatbelt_law: Optional[bool] = None
    data_year: Optional[int] = None
    source: str = "WHO Global Status Report / GHO (static snapshot)"
    is_sample: bool = False
    note: Optional[str] = None


class CountryIndicatorsResponse(BaseModel):
    """Response for country indicators."""
    updated_at: str
    countries: List[CountryIndicator]


def _sample_country_indicators() -> List[CountryIndicator]:
    """Static country indicators (manually curated snapshot; update when ingesting live feeds)."""
    sample = [
        {
            "country_code": "IND",
            "country_name": "India",
            "deaths_per_100k": 15.6,
            "helmet_law": True,
            "seatbelt_law": True,
            "data_year": 2023,
            "note": "Static WHO/GHO snapshot; refresh from latest releases."
        },
        {
            "country_code": "USA",
            "country_name": "United States",
            "deaths_per_100k": 12.0,
            "helmet_law": False,
            "seatbelt_law": True,
            "data_year": 2023,
            "note": "Static snapshot; state-level helmet laws vary."
        },
        {
            "country_code": "BRA",
            "country_name": "Brazil",
            "deaths_per_100k": 18.3,
            "helmet_law": True,
            "seatbelt_law": True,
            "data_year": 2023,
            "note": "Static snapshot."
        },
        {
            "country_code": "DEU",
            "country_name": "Germany",
            "deaths_per_100k": 4.2,
            "helmet_law": True,
            "seatbelt_law": True,
            "data_year": 2023,
            "note": "Static snapshot."
        },
        {
            "country_code": "GBR",
            "country_name": "United Kingdom",
            "deaths_per_100k": 2.9,
            "helmet_law": True,
            "seatbelt_law": True,
            "data_year": 2023,
            "note": "Static snapshot."
        },
        {
            "country_code": "FRA",
            "country_name": "France",
            "deaths_per_100k": 4.7,
            "helmet_law": True,
            "seatbelt_law": True,
            "data_year": 2023,
            "note": "Static snapshot."
        },
        {
            "country_code": "AUS",
            "country_name": "Australia",
            "deaths_per_100k": 4.1,
            "helmet_law": True,
            "seatbelt_law": True,
            "data_year": 2023,
            "note": "Static snapshot."
        },
        {
            "country_code": "CAN",
            "country_name": "Canada",
            "deaths_per_100k": 4.6,
            "helmet_law": True,
            "seatbelt_law": True,
            "data_year": 2023,
            "note": "Static snapshot; helmet varies by province."
        },
        {
            "country_code": "ZAF",
            "country_name": "South Africa",
            "deaths_per_100k": 22.2,
            "helmet_law": True,
            "seatbelt_law": True,
            "data_year": 2023,
            "note": "Static snapshot."
        },
        {
            "country_code": "IDN",
            "country_name": "Indonesia",
            "deaths_per_100k": 12.2,
            "helmet_law": True,
            "seatbelt_law": True,
            "data_year": 2023,
            "note": "Static snapshot."
        },
        {
            "country_code": "MEX",
            "country_name": "Mexico",
            "deaths_per_100k": 13.1,
            "helmet_law": True,
            "seatbelt_law": True,
            "data_year": 2023,
            "note": "Static snapshot."
        },
    ]
    return [CountryIndicator(**item) for item in sample]


@router.get("/global/indicators", response_model=CountryIndicatorsResponse)
async def get_country_indicators(country: Optional[str] = None):
    """Provide demo country indicators for UI; replace with live data feeds.

    Args:
        country: Optional country code/name filter

    Returns:
        Country indicator list with demo placeholders
    """
    indicators = _sample_country_indicators()
    if country:
        lowered = country.lower()
        indicators = [c for c in indicators if c.country_code.lower() == lowered or c.country_name.lower() == lowered]
    return CountryIndicatorsResponse(
        updated_at=datetime.now().isoformat(),
        countries=indicators,
    )


# ============== GLOBAL TRAFFIC RULES (STATIC SNAPSHOT) ==============


class TrafficRule(BaseModel):
    """A single traffic rule or policy item."""
    title: str
    description: str
    penalty: Optional[str] = None
    source: str = "Gov/official guidance"


class StateTrafficRules(BaseModel):
    """Traffic rules scoped to a state/province."""
    state_name: str
    rules: List[TrafficRule]


class CountryTrafficRules(BaseModel):
    """Traffic rules for a country, optionally with state-level details."""
    country_code: str
    country_name: str
    rules: List[TrafficRule]
    states: Optional[List[StateTrafficRules]] = None
    data_year: Optional[int] = None
    note: Optional[str] = None


class TrafficRulesResponse(BaseModel):
    """Response wrapper for traffic rules."""
    updated_at: str
    countries: List[CountryTrafficRules]


class StateInfo(BaseModel):
    """State/province descriptor."""
    code: str
    name: str
    note: Optional[str] = None


class CountryStates(BaseModel):
    """States for a country."""
    country_code: str
    country_name: str
    states: List[StateInfo]


class TrafficStatesResponse(BaseModel):
    """Response for country state lists."""
    updated_at: str
    countries: List[CountryStates]


def _sample_traffic_rules() -> List[CountryTrafficRules]:
    """Static traffic rules (manually curated snapshot)."""
    return [
        CountryTrafficRules(
            country_code="IND",
            country_name="India",
            data_year=2023,
            note="Motor Vehicles Act with state enforcement variations",
            rules=[
                TrafficRule(title="Helmet mandatory (two-wheelers)", description="All riders and pillion must wear BIS-certified helmets.", penalty="₹1,000 fine"),
                TrafficRule(title="Seatbelt mandatory", description="All occupants in front seats must wear seatbelts; many states enforce rear belts in cities.", penalty="₹1,000 fine"),
                TrafficRule(title="Speed limits", description="Varies by road class; highways typically 80–100 km/h unless otherwise notified."),
                TrafficRule(title="Drink-driving limit", description="BAC ≤ 0.03%.", penalty="Fine/jail per MVA"),
            ],
            states=[
                StateTrafficRules(
                    state_name="Tamil Nadu",
                    rules=[
                        TrafficRule(title="Helmet enforcement", description="Strict enforcement in Chennai and major corridors."),
                        TrafficRule(title="Speed cameras", description="Automated enforcement on key NH/SH corridors."),
                    ],
                ),
                StateTrafficRules(
                    state_name="Karnataka",
                    rules=[
                        TrafficRule(title="Rear seatbelt advisory", description="Enforced in Bengaluru urban limits."),
                        TrafficRule(title="Helmet for pillion", description="Actively enforced in urban areas."),
                    ],
                ),
            ],
        ),
        CountryTrafficRules(
            country_code="USA",
            country_name="United States",
            data_year=2023,
            note="State-level variation is significant",
            rules=[
                TrafficRule(title="Seatbelt", description="Front seat mandatory nationwide; rear varies by state."),
                TrafficRule(title="Helmet laws", description="Vary by state; many require for riders under a certain age."),
                TrafficRule(title="Speed limits", description="Typically 55–75 mph by state and road type."),
            ],
            states=[
                StateTrafficRules(
                    state_name="California",
                    rules=[
                        TrafficRule(title="Motorcycle helmet", description="Universal helmet law."),
                        TrafficRule(title="Hands-free", description="Handheld phone use banned while driving."),
                    ],
                ),
                StateTrafficRules(
                    state_name="Texas",
                    rules=[
                        TrafficRule(title="Helmet for riders <21", description="Mandatory below age 21 (with exceptions)."),
                        TrafficRule(title="Speed limits", description="Up to 85 mph on designated toll roads."),
                    ],
                ),
            ],
        ),
        CountryTrafficRules(
            country_code="DEU",
            country_name="Germany",
            data_year=2023,
            note="StVO national rules; Autobahn segments without numeric limit but advisory 130 km/h",
            rules=[
                TrafficRule(title="Seatbelt", description="Mandatory for all occupants."),
                TrafficRule(title="Helmet", description="Mandatory for motorcycles."),
                TrafficRule(title="Drink-driving limit", description="BAC ≤ 0.05%; lower for novice/pro drivers."),
            ],
            states=None,
        ),
        CountryTrafficRules(
            country_code="BRA",
            country_name="Brazil",
            data_year=2023,
            rules=[
                TrafficRule(title="Seatbelt", description="Mandatory for all occupants."),
                TrafficRule(title="Helmet", description="Mandatory for motorcycles."),
                TrafficRule(title="Speed limits", description="Urban default 30–50 km/h; highways 80–110 km/h depending on class."),
            ],
            note="CTB national rules; enforcement varies by state",
        ),
        CountryTrafficRules(
            country_code="CAN",
            country_name="Canada",
            data_year=2023,
            note="Provincial variation for helmets and penalties",
            rules=[
                TrafficRule(title="Seatbelt", description="Mandatory for all occupants; fines vary by province."),
                TrafficRule(title="Helmet (motorcycle)", description="Mandatory in all provinces/territories."),
                TrafficRule(title="Impaired driving", description="Criminal Code nationwide; provincial penalties vary."),
            ],
            states=[
                StateTrafficRules(
                    state_name="Ontario",
                    rules=[
                        TrafficRule(title="Distracted driving", description="Handheld devices banned; escalating fines and points."),
                        TrafficRule(title="Speeding", description="Stunt driving at 40 km/h over limit below 80 km/h, or 50+ over otherwise."),
                    ],
                ),
                StateTrafficRules(
                    state_name="British Columbia",
                    rules=[
                        TrafficRule(title="Distracted driving", description="Handheld ban; fines and points."),
                        TrafficRule(title="Speeding", description="Higher fines for excessive speeding >40 km/h over."),
                    ],
                ),
            ],
        ),
        CountryTrafficRules(
            country_code="FRA",
            country_name="France",
            data_year=2023,
            note="Code de la route; nationwide rules",
            rules=[
                TrafficRule(title="Seatbelt", description="Mandatory for all occupants."),
                TrafficRule(title="Helmet", description="Mandatory for motorcycles; hi-vis for riders outside urban areas at night."),
                TrafficRule(title="Speed limits", description="130 km/h motorways (110 if rain), 80–90 km/h rural, 50 km/h urban unless posted."),
                TrafficRule(title="Drink-driving", description="BAC ≤ 0.05%; 0.02% for novice/pro."),
            ],
        ),
        CountryTrafficRules(
            country_code="ESP",
            country_name="Spain",
            data_year=2023,
            note="DGT nationwide rules",
            rules=[
                TrafficRule(title="Seatbelt", description="Mandatory for all occupants."),
                TrafficRule(title="Helmet", description="Mandatory for motorcycles and mopeds."),
                TrafficRule(title="Speed limits", description="120 km/h motorways, 90 km/h rural, 30–50 km/h urban depending on street type."),
                TrafficRule(title="Drink-driving", description="BAC ≤ 0.05%; 0.03% for novice/pro."),
            ],
        ),
        CountryTrafficRules(
            country_code="ITA",
            country_name="Italy",
            data_year=2023,
            note="Codice della Strada; national rules",
            rules=[
                TrafficRule(title="Seatbelt", description="Mandatory for all occupants."),
                TrafficRule(title="Helmet", description="Mandatory for motorcycles."),
                TrafficRule(title="Speed limits", description="130 km/h motorways (110 in rain), 90 km/h rural, 50 km/h urban."),
                TrafficRule(title="Drink-driving", description="BAC ≤ 0.05%; 0.00% for novice/pro."),
            ],
        ),
        CountryTrafficRules(
            country_code="NLD",
            country_name="Netherlands",
            data_year=2023,
            note="Nationwide rules; strong cycling protections",
            rules=[
                TrafficRule(title="Seatbelt", description="Mandatory for all occupants."),
                TrafficRule(title="Helmet", description="Mandatory for motorcycles; speed-pedelecs require helmets."),
                TrafficRule(title="Speed limits", description="100 km/h motorways daytime, 120/130 km/h off-peak; 80 km/h rural; 30–50 km/h urban."),
                TrafficRule(title="Drink-driving", description="BAC ≤ 0.05%; 0.02% for novice."),
            ],
        ),
        CountryTrafficRules(
            country_code="SWE",
            country_name="Sweden",
            data_year=2023,
            note="Vision Zero framework; national rules",
            rules=[
                TrafficRule(title="Seatbelt", description="Mandatory for all occupants."),
                TrafficRule(title="Helmet", description="Mandatory for motorcycles; bicycle helmets required under 15."),
                TrafficRule(title="Speed limits", description="Variable by road design; many rural roads 80–100 km/h, urban 30–50 km/h."),
                TrafficRule(title="Drink-driving", description="BAC ≤ 0.02%."),
            ],
        ),
    ]


def _country_states_catalog() -> List[CountryStates]:
    """Static ISO/state list for covered countries."""
    return [
        CountryStates(
            country_code="IND",
            country_name="India",
            states=[
                StateInfo(code="AN", name="Andaman and Nicobar Islands"),
                StateInfo(code="AP", name="Andhra Pradesh"),
                StateInfo(code="AR", name="Arunachal Pradesh"),
                StateInfo(code="AS", name="Assam"),
                StateInfo(code="BR", name="Bihar"),
                StateInfo(code="CH", name="Chandigarh"),
                StateInfo(code="CT", name="Chhattisgarh"),
                StateInfo(code="DN", name="Dadra and Nagar Haveli and Daman and Diu"),
                StateInfo(code="DL", name="Delhi"),
                StateInfo(code="GA", name="Goa"),
                StateInfo(code="GJ", name="Gujarat"),
                StateInfo(code="HR", name="Haryana"),
                StateInfo(code="HP", name="Himachal Pradesh"),
                StateInfo(code="JK", name="Jammu and Kashmir"),
                StateInfo(code="JH", name="Jharkhand"),
                StateInfo(code="KA", name="Karnataka"),
                StateInfo(code="KL", name="Kerala"),
                StateInfo(code="LA", name="Ladakh"),
                StateInfo(code="LD", name="Lakshadweep"),
                StateInfo(code="MP", name="Madhya Pradesh"),
                StateInfo(code="MH", name="Maharashtra"),
                StateInfo(code="MN", name="Manipur"),
                StateInfo(code="ML", name="Meghalaya"),
                StateInfo(code="MZ", name="Mizoram"),
                StateInfo(code="NL", name="Nagaland"),
                StateInfo(code="OR", name="Odisha"),
                StateInfo(code="PY", name="Puducherry"),
                StateInfo(code="PB", name="Punjab"),
                StateInfo(code="RJ", name="Rajasthan"),
                StateInfo(code="SK", name="Sikkim"),
                StateInfo(code="TN", name="Tamil Nadu"),
                StateInfo(code="TS", name="Telangana"),
                StateInfo(code="TR", name="Tripura"),
                StateInfo(code="UP", name="Uttar Pradesh"),
                StateInfo(code="UT", name="Uttarakhand"),
                StateInfo(code="WB", name="West Bengal"),
            ],
        ),
        CountryStates(
            country_code="USA",
            country_name="United States",
            states=[
                StateInfo(code="AL", name="Alabama"), StateInfo(code="AK", name="Alaska"), StateInfo(code="AZ", name="Arizona"),
                StateInfo(code="AR", name="Arkansas"), StateInfo(code="CA", name="California"), StateInfo(code="CO", name="Colorado"),
                StateInfo(code="CT", name="Connecticut"), StateInfo(code="DE", name="Delaware"), StateInfo(code="DC", name="District of Columbia"),
                StateInfo(code="FL", name="Florida"), StateInfo(code="GA", name="Georgia"), StateInfo(code="HI", name="Hawaii"),
                StateInfo(code="ID", name="Idaho"), StateInfo(code="IL", name="Illinois"), StateInfo(code="IN", name="Indiana"),
                StateInfo(code="IA", name="Iowa"), StateInfo(code="KS", name="Kansas"), StateInfo(code="KY", name="Kentucky"),
                StateInfo(code="LA", name="Louisiana"), StateInfo(code="ME", name="Maine"), StateInfo(code="MD", name="Maryland"),
                StateInfo(code="MA", name="Massachusetts"), StateInfo(code="MI", name="Michigan"), StateInfo(code="MN", name="Minnesota"),
                StateInfo(code="MS", name="Mississippi"), StateInfo(code="MO", name="Missouri"), StateInfo(code="MT", name="Montana"),
                StateInfo(code="NE", name="Nebraska"), StateInfo(code="NV", name="Nevada"), StateInfo(code="NH", name="New Hampshire"),
                StateInfo(code="NJ", name="New Jersey"), StateInfo(code="NM", name="New Mexico"), StateInfo(code="NY", name="New York"),
                StateInfo(code="NC", name="North Carolina"), StateInfo(code="ND", name="North Dakota"), StateInfo(code="OH", name="Ohio"),
                StateInfo(code="OK", name="Oklahoma"), StateInfo(code="OR", name="Oregon"), StateInfo(code="PA", name="Pennsylvania"),
                StateInfo(code="RI", name="Rhode Island"), StateInfo(code="SC", name="South Carolina"), StateInfo(code="SD", name="South Dakota"),
                StateInfo(code="TN", name="Tennessee"), StateInfo(code="TX", name="Texas"), StateInfo(code="UT", name="Utah"),
                StateInfo(code="VT", name="Vermont"), StateInfo(code="VA", name="Virginia"), StateInfo(code="WA", name="Washington"),
                StateInfo(code="WV", name="West Virginia"), StateInfo(code="WI", name="Wisconsin"), StateInfo(code="WY", name="Wyoming"),
            ],
        ),
        CountryStates(
            country_code="CAN",
            country_name="Canada",
            states=[
                StateInfo(code="AB", name="Alberta"), StateInfo(code="BC", name="British Columbia"), StateInfo(code="MB", name="Manitoba"),
                StateInfo(code="NB", name="New Brunswick"), StateInfo(code="NL", name="Newfoundland and Labrador"), StateInfo(code="NS", name="Nova Scotia"),
                StateInfo(code="NT", name="Northwest Territories"), StateInfo(code="NU", name="Nunavut"), StateInfo(code="ON", name="Ontario"),
                StateInfo(code="PE", name="Prince Edward Island"), StateInfo(code="QC", name="Quebec"), StateInfo(code="SK", name="Saskatchewan"),
                StateInfo(code="YT", name="Yukon"),
            ],
        ),
        CountryStates(
            country_code="DEU",
            country_name="Germany",
            states=[
                StateInfo(code="BW", name="Baden-Wuerttemberg"), StateInfo(code="BY", name="Bavaria"), StateInfo(code="BE", name="Berlin"),
                StateInfo(code="BB", name="Brandenburg"), StateInfo(code="HB", name="Bremen"), StateInfo(code="HH", name="Hamburg"),
                StateInfo(code="HE", name="Hesse"), StateInfo(code="MV", name="Mecklenburg-Western Pomerania"), StateInfo(code="NI", name="Lower Saxony"),
                StateInfo(code="NW", name="North Rhine-Westphalia"), StateInfo(code="RP", name="Rhineland-Palatinate"), StateInfo(code="SL", name="Saarland"),
                StateInfo(code="SN", name="Saxony"), StateInfo(code="ST", name="Saxony-Anhalt"), StateInfo(code="SH", name="Schleswig-Holstein"),
                StateInfo(code="TH", name="Thuringia"),
            ],
        ),
        CountryStates(
            country_code="FRA",
            country_name="France",
            states=[
                StateInfo(code="ARA", name="Auvergne-Rhone-Alpes"), StateInfo(code="BFC", name="Bourgogne-Franche-Comte"),
                StateInfo(code="BRE", name="Bretagne"), StateInfo(code="CVL", name="Centre-Val de Loire"), StateInfo(code="COR", name="Corse"),
                StateInfo(code="GES", name="Grand Est"), StateInfo(code="HDF", name="Hauts-de-France"), StateInfo(code="IDF", name="Ile-de-France"),
                StateInfo(code="NOR", name="Normandie"), StateInfo(code="NAQ", name="Nouvelle-Aquitaine"), StateInfo(code="OCC", name="Occitanie"),
                StateInfo(code="PAC", name="Provence-Alpes-Cote d'Azur"), StateInfo(code="PDL", name="Pays de la Loire"),
                StateInfo(code="GUA", name="Guadeloupe"), StateInfo(code="GUF", name="Guyane"), StateInfo(code="MAY", name="Mayotte"),
                StateInfo(code="LRE", name="La Reunion"), StateInfo(code="MTQ", name="Martinique"),
            ],
        ),
        CountryStates(
            country_code="ESP",
            country_name="Spain",
            states=[
                StateInfo(code="AN", name="Andalucia"), StateInfo(code="AR", name="Aragon"), StateInfo(code="AS", name="Asturias"),
                StateInfo(code="CN", name="Canarias"), StateInfo(code="CB", name="Cantabria"), StateInfo(code="CM", name="Castilla-La Mancha"),
                StateInfo(code="CL", name="Castilla y Leon"), StateInfo(code="CT", name="Cataluna"), StateInfo(code="EX", name="Extremadura"),
                StateInfo(code="GA", name="Galicia"), StateInfo(code="IB", name="Islas Baleares"), StateInfo(code="RI", name="La Rioja"),
                StateInfo(code="MD", name="Madrid"), StateInfo(code="MC", name="Murcia"), StateInfo(code="NC", name="Navarra"),
                StateInfo(code="PV", name="Pais Vasco"), StateInfo(code="VC", name="Comunidad Valenciana"), StateInfo(code="CE", name="Ceuta"),
                StateInfo(code="ML", name="Melilla"),
            ],
        ),
        CountryStates(
            country_code="ITA",
            country_name="Italy",
            states=[
                StateInfo(code="ABR", name="Abruzzo"), StateInfo(code="BAS", name="Basilicata"), StateInfo(code="CAL", name="Calabria"),
                StateInfo(code="CAM", name="Campania"), StateInfo(code="EMR", name="Emilia-Romagna"), StateInfo(code="FVG", name="Friuli-Venezia Giulia"),
                StateInfo(code="LAZ", name="Lazio"), StateInfo(code="LIG", name="Liguria"), StateInfo(code="LOM", name="Lombardia"),
                StateInfo(code="MAR", name="Marche"), StateInfo(code="MOL", name="Molise"), StateInfo(code="PIE", name="Piemonte"),
                StateInfo(code="PUG", name="Puglia"), StateInfo(code="SAR", name="Sardegna"), StateInfo(code="SIC", name="Sicilia"),
                StateInfo(code="TOS", name="Toscana"), StateInfo(code="TAA", name="Trentino-Alto Adige"), StateInfo(code="UMB", name="Umbria"),
                StateInfo(code="VDA", name="Valle d'Aosta"), StateInfo(code="VEN", name="Veneto"),
            ],
        ),
        CountryStates(
            country_code="NLD",
            country_name="Netherlands",
            states=[
                StateInfo(code="DR", name="Drenthe"), StateInfo(code="FL", name="Flevoland"), StateInfo(code="FR", name="Fryslan"),
                StateInfo(code="GE", name="Gelderland"), StateInfo(code="GR", name="Groningen"), StateInfo(code="LI", name="Limburg"),
                StateInfo(code="NB", name="Noord-Brabant"), StateInfo(code="NH", name="Noord-Holland"), StateInfo(code="OV", name="Overijssel"),
                StateInfo(code="UT", name="Utrecht"), StateInfo(code="ZE", name="Zeeland"), StateInfo(code="ZH", name="Zuid-Holland"),
            ],
        ),
        CountryStates(
            country_code="SWE",
            country_name="Sweden",
            states=[
                StateInfo(code="AB", name="Stockholm"), StateInfo(code="AC", name="Vasterbotten"), StateInfo(code="BD", name="Norrbotten"),
                StateInfo(code="C", name="Uppsala"), StateInfo(code="D", name="Sodermanland"), StateInfo(code="E", name="Ostergotland"),
                StateInfo(code="F", name="Jonkoping"), StateInfo(code="G", name="Kronoberg"), StateInfo(code="H", name="Kalmar"),
                StateInfo(code="I", name="Gotland"), StateInfo(code="K", name="Blekinge"), StateInfo(code="N", name="Halland"),
                StateInfo(code="M", name="Skane"), StateInfo(code="O", name="Vastra Gotaland"), StateInfo(code="S", name="Varmland"),
                StateInfo(code="T", name="Orebro"), StateInfo(code="U", name="Vastmanland"), StateInfo(code="W", name="Dalarna"),
                StateInfo(code="X", name="Gavleborg"), StateInfo(code="Y", name="Vasternorrland"), StateInfo(code="Z", name="Jamtland"),
            ],
        ),
        CountryStates(
            country_code="BRA",
            country_name="Brazil",
            states=[
                StateInfo(code="AC", name="Acre"), StateInfo(code="AL", name="Alagoas"), StateInfo(code="AP", name="Amapa"), StateInfo(code="AM", name="Amazonas"),
                StateInfo(code="BA", name="Bahia"), StateInfo(code="CE", name="Ceara"), StateInfo(code="DF", name="Distrito Federal"), StateInfo(code="ES", name="Espirito Santo"),
                StateInfo(code="GO", name="Goias"), StateInfo(code="MA", name="Maranhao"), StateInfo(code="MT", name="Mato Grosso"), StateInfo(code="MS", name="Mato Grosso do Sul"),
                StateInfo(code="MG", name="Minas Gerais"), StateInfo(code="PA", name="Para"), StateInfo(code="PB", name="Paraiba"), StateInfo(code="PR", name="Parana"),
                StateInfo(code="PE", name="Pernambuco"), StateInfo(code="PI", name="Piaui"), StateInfo(code="RJ", name="Rio de Janeiro"), StateInfo(code="RN", name="Rio Grande do Norte"),
                StateInfo(code="RS", name="Rio Grande do Sul"), StateInfo(code="RO", name="Rondonia"), StateInfo(code="RR", name="Roraima"), StateInfo(code="SC", name="Santa Catarina"),
                StateInfo(code="SP", name="Sao Paulo"), StateInfo(code="SE", name="Sergipe"), StateInfo(code="TO", name="Tocantins"),
            ],
        ),
    ]


@router.get("/global/traffic-rules", response_model=TrafficRulesResponse)
async def get_traffic_rules(country: Optional[str] = None, state: Optional[str] = None):
    """Return static traffic rules by country, optionally filtered by state/province."""
    data = _sample_traffic_rules()

    if country:
        lowered = country.lower()
        data = [c for c in data if c.country_code.lower() == lowered or c.country_name.lower() == lowered]

    if state and data:
        state_lower = state.lower()
        filtered = []
        for c in data:
            if not c.states:
                filtered.append(c)
                continue
            matched_states = [s for s in c.states if s.state_name.lower() == state_lower]
            filtered.append(CountryTrafficRules(
                country_code=c.country_code,
                country_name=c.country_name,
                rules=c.rules,
                states=matched_states or None,
                data_year=c.data_year,
                note=c.note,
            ))
        data = filtered

    return TrafficRulesResponse(
        updated_at=datetime.now().isoformat(),
        countries=data,
    )


@router.get("/global/traffic-rules/states", response_model=TrafficStatesResponse)
async def get_country_states(country: Optional[str] = None):
    """Return state/province lists for supported countries."""
    catalog = _country_states_catalog()
    if country:
        lowered = country.lower()
        catalog = [c for c in catalog if c.country_code.lower() == lowered or c.country_name.lower() == lowered]
    return TrafficStatesResponse(
        updated_at=datetime.now().isoformat(),
        countries=catalog,
    )


# ============== Batch Predictions ==============

class BatchRiskRequest(BaseModel):
    """Request for batch risk predictions."""
    predictions: List[RiskPredictionRequest] = Field(..., min_items=1, max_items=1000)


class BatchRiskResponse(BaseModel):
    """Response for batch risk predictions."""
    results: List[RiskPredictionResponse]
    processing_time_ms: float
    failed_count: int


@router.post("/predict/batch-risk", response_model=BatchRiskResponse)
@track_prediction_latency("lstm_batch")
async def batch_predict_risk(request: BatchRiskRequest):
    """Predict risk for multiple traffic records in batch.
    
    Args:
        request: Batch of RiskPredictionRequests
    
    Returns:
        Batch of risk predictions with timing stats
    """
    import time
    start = time.time()
    
    results = []
    failed = 0
    
    for pred_req in request.predictions:
        try:
            result = await predict_risk(pred_req)
            results.append(result)
        except Exception as e:
            failed += 1
            results.append(RiskPredictionResponse(
                road_segment_id=pred_req.road_segment_id,
                risk_score=0.5,
                risk_label="MEDIUM",
                confidence=0.0,
                error=str(e),
            ))
    
    processing_time = (time.time() - start) * 1000
    
    return BatchRiskResponse(
        results=results,
        processing_time_ms=processing_time,
        failed_count=failed,
    )


# ============== Time-Series Forecasting ==============

class ForecastRequest(BaseModel):
    """Request for risk forecast."""
    road_segment_id: str
    forecast_hours: int = Field(24, ge=1, le=168)  # 1-7 days


class ForecastPoint(BaseModel):
    """Single forecast point."""
    timestamp: str
    predicted_risk: float
    confidence_interval_lower: float
    confidence_interval_upper: float


class ForecastResponse(BaseModel):
    """Risk forecast response."""
    road_segment_id: str
    forecast: List[ForecastPoint]


@router.post("/forecast/risk", response_model=ForecastResponse)
async def forecast_risk(request: ForecastRequest):
    """Forecast risk for next N hours using LSTM.
    
    Simple autoregressive forecasting: use last prediction as input for next step.
    """
    # Placeholder: in production, maintain per-segment time series state
    now = datetime.now()
    forecast = []
    
    current_risk = 0.5
    for i in range(request.forecast_hours):
        timestamp = now + timedelta(hours=i)
        
        # Simple trend: risk slightly decreases over time (demo)
        predicted_risk = max(0, current_risk - 0.01 * i)
        
        # Confidence interval widens with forecast horizon
        ci_width = 0.1 * (i + 1) / request.forecast_hours
        
        forecast.append(ForecastPoint(
            timestamp=timestamp.isoformat(),
            predicted_risk=predicted_risk,
            confidence_interval_lower=max(0, predicted_risk - ci_width),
            confidence_interval_upper=min(1, predicted_risk + ci_width),
        ))
        
        current_risk = predicted_risk
    
    return ForecastResponse(
        road_segment_id=request.road_segment_id,
        forecast=forecast,
    )


# ============== Alert Rules ==============

class AlertRule(BaseModel):
    """Alert rule definition."""
    segment_id: str
    risk_threshold: float = Field(0.7, ge=0, le=1)
    severity_threshold: int = Field(2, ge=0, le=3)  # 0=no_injury, 3=fatal
    alert_cooldown_minutes: int = 30


class AlertRulesResponse(BaseModel):
    """Active alert rules."""
    rules: List[AlertRule]


@router.get("/alerts/rules", response_model=AlertRulesResponse)
async def list_alert_rules():
    """List all active alert rules."""
    # Placeholder: in production, load from database
    rules = [
        AlertRule(segment_id="S1", risk_threshold=0.75),
        AlertRule(segment_id="S2", risk_threshold=0.70),
    ]
    return AlertRulesResponse(rules=rules)


@router.post("/alerts/rules")
async def create_alert_rule(rule: AlertRule):
    """Create a new alert rule.
    
    Args:
        rule: Alert rule configuration
    
    Returns:
        Confirmation with rule ID
    """
    # Placeholder: save to database
    return {"rule_id": "alert_rule_1", "status": "created", "rule": rule}


# ============== Model Drift Detection ==============

class DriftDetectionRequest(BaseModel):
    """Request for model drift detection."""
    model_type: str = Field(..., description="'risk' (LSTM) or 'severity' (RF)")
    recent_samples: int = 1000  # Evaluate on recent N predictions


class DriftMetric(BaseModel):
    """Single drift metric."""
    metric_name: str
    value: float
    threshold: float
    is_drifted: bool


class DriftDetectionResponse(BaseModel):
    """Model drift detection response."""
    model_type: str
    drift_score: float  # 0-1, higher = more drift
    is_drifted: bool  # True if any metric exceeds threshold
    metrics: List[DriftMetric]
    recommendation: str


@router.post("/monitoring/drift-detection", response_model=DriftDetectionResponse)
async def detect_model_drift(request: DriftDetectionRequest):
    """Detect if model has drifted from training distribution.
    
    Checks for:
    - Input distribution shift (features)
    - Output distribution shift (predictions)
    - Prediction confidence decline
    """
    if request.model_type not in ["risk", "severity"]:
        raise HTTPException(status_code=400, detail="Invalid model_type")
    
    # Placeholder metrics (in production, compute from recent predictions)
    metrics = [
        DriftMetric(
            metric_name="input_mean_shift",
            value=0.05,
            threshold=0.2,
            is_drifted=False,
        ),
        DriftMetric(
            metric_name="prediction_std_deviation",
            value=0.15,
            threshold=0.05,
            is_drifted=True,  # Elevated variance = potential drift
        ),
        DriftMetric(
            metric_name="confidence_decline",
            value=0.08,
            threshold=0.1,
            is_drifted=False,
        ),
    ]
    
    drift_score = np.mean([m.value / m.threshold for m in metrics])
    is_drifted = any(m.is_drifted for m in metrics)
    
    recommendation = "Model retraining recommended" if is_drifted else "Model performing normally"
    
    return DriftDetectionResponse(
        model_type=request.model_type,
        drift_score=min(drift_score, 1.0),
        is_drifted=is_drifted,
        metrics=metrics,
        recommendation=recommendation,
    )


# ============== Model Performance Stats ==============

class PerformanceStatsResponse(BaseModel):
    """Model performance statistics."""
    model_type: str
    accuracy: float
    precision: float
    recall: float
    f1_score: float
    auc_roc: float
    predictions_count: int
    last_updated: str


@router.get("/monitoring/performance/{model_type}", response_model=PerformanceStatsResponse)
async def get_model_performance(model_type: str):
    """Get current performance metrics for a model.
    
    Args:
        model_type: 'risk' or 'severity'
    
    Returns:
        Performance metrics computed on recent predictions
    """
    if model_type not in ["risk", "severity"]:
        raise HTTPException(status_code=400, detail="Invalid model_type")
    
    # Placeholder: in production, compute from recent predictions vs actual outcomes
    return PerformanceStatsResponse(
        model_type=model_type,
        accuracy=0.92,
        precision=0.88,
        recall=0.90,
        f1_score=0.89,
        auc_roc=0.95,
        predictions_count=15234,
        last_updated=datetime.now().isoformat(),
    )


# ============== Critical Spots & Maps ==============


class CriticalSpot(BaseModel):
    """Top risk segments for the upcoming window."""
    segment_id: str
    road_name: str = "NH44"  # Road/highway name for police
    kilometers: str = "23-25 km"  # Location on road
    risk_score: float
    severity_label: str
    reasons: List[str]
    recommended_actions: List[str]
    color: str = Field(..., description="Map-friendly color (red/orange/yellow/green)")
    window: str = "tonight"


class CriticalSpotsResponse(BaseModel):
    """Response for top critical spots."""
    generated_at: str
    window: str
    spots: List[CriticalSpot]


def _sample_critical_spots() -> List[CriticalSpot]:
    """Static sample data for critical spots and map payloads."""
    base = [
        {
            "segment_id": "S42",
            "road_name": "NH44_Hosur",
            "kilometers": "23-25 km",
            "risk_score": 0.92,
            "severity_label": "HIGH",
            "reasons": ["Heavy rain", "Peak-hour congestion", "Recent near-miss"],
            "recommended_actions": ["Reduce speed limits", "Deploy patrol", "Dynamic signage"],
            "color": "red",
        },
        {
            "segment_id": "S18",
            "road_name": "NH44_Hosur",
            "kilometers": "18-20 km",
            "risk_score": 0.85,
            "severity_label": "HIGH",
            "reasons": ["Fog/low visibility", "Sharp curve", "Speed variance rising"],
            "recommended_actions": ["Activate fog beacons", "Increase enforcement", "Push navigation alerts"],
            "color": "red",
        },
        {
            "segment_id": "S7",
            "road_name": "NH44_Hosur",
            "kilometers": "7-9 km",
            "risk_score": 0.81,
            "severity_label": "MEDIUM",
            "reasons": ["Lane closure", "Queue spillback risk"],
            "recommended_actions": ["Update variable message signs", "Adjust signal timing"],
            "color": "orange",
        },
        {
            "segment_id": "S3",
            "road_name": "NH44_Hosur",
            "kilometers": "3-5 km",
            "risk_score": 0.78,
            "severity_label": "MEDIUM",
            "reasons": ["Wet pavement", "Nighttime"],
            "recommended_actions": ["Advisory speed reduction", "Enable roadway lighting"],
            "color": "orange",
        },
        {
            "segment_id": "S12",
            "road_name": "NH44_Hosur",
            "kilometers": "12-14 km",
            "risk_score": 0.74,
            "severity_label": "MEDIUM",
            "reasons": ["Work zone", "Short merge"],
            "recommended_actions": ["Extend taper", "Deploy cones", "Send driver push alerts"],
            "color": "orange",
        },
        {
            "segment_id": "S25",
            "road_name": "NH44_Hosur",
            "kilometers": "25-27 km",
            "risk_score": 0.70,
            "severity_label": "MEDIUM",
            "reasons": ["High truck volume", "Crosswind"],
            "recommended_actions": ["Advisory for high-profile vehicles", "Monitor gust sensors"],
            "color": "yellow",
        },
        {
            "segment_id": "S31",
            "road_name": "NH44_Hosur",
            "kilometers": "31-33 km",
            "risk_score": 0.66,
            "severity_label": "MEDIUM",
            "reasons": ["Minor precipitation", "Evening peak"],
            "recommended_actions": ["Fine-tune ramp metering", "Promote alt routes"],
            "color": "yellow",
        },
        {
            "segment_id": "S5",
            "road_name": "NH44_Hosur",
            "kilometers": "5-7 km",
            "risk_score": 0.63,
            "severity_label": "LOW",
            "reasons": ["Speed variability", "Off-ramp backups"],
            "recommended_actions": ["Queue warning signs", "Adjust signal offsets"],
            "color": "yellow",
        },
        {
            "segment_id": "S8",
            "road_name": "NH44_Hosur",
            "kilometers": "8-10 km",
            "risk_score": 0.61,
            "severity_label": "LOW",
            "reasons": ["Light rain", "Lane changing spikes"],
            "recommended_actions": ["Driver advisory", "Short-term enforcement"],
            "color": "yellow",
        },
        {
            "segment_id": "S19",
            "road_name": "NH44_Hosur",
            "kilometers": "19-21 km",
            "risk_score": 0.59,
            "severity_label": "LOW",
            "reasons": ["Nighttime", "Historical hotspot"],
            "recommended_actions": ["Lighting check", "Targeted patrol"],
            "color": "yellow",
        },
    ]
    return [CriticalSpot(**item) for item in base]


@router.get("/reports/critical-spots", response_model=CriticalSpotsResponse)
async def get_critical_spots():
    """Return top-10 critical spots for tonight with reasons and actions."""
    spots = _sample_critical_spots()
    return CriticalSpotsResponse(
        generated_at=datetime.now().isoformat(),
        window="tonight",
        spots=spots,
    )


class MapSegment(BaseModel):
    """Map-ready segment payload."""
    segment_id: str
    latitude: float
    longitude: float
    risk_score: float
    color: str
    reasons: List[str]
    recommended_actions: List[str]
    geometry_type: str = "point"  # Could be 'point', 'linestring' for polyline


class MapReadyResponse(BaseModel):
    """Map payload for critical spots."""
    generated_at: str
    projection: str
    segments: List[MapSegment]


@router.get("/maps/critical-spots", response_model=MapReadyResponse)
async def map_ready_critical_spots(country: Optional[str] = None, state: Optional[str] = None):
    """Map-ready JSON for critical segments (segment_id, risk, color, reasons, actions).

    Args:
        country: Optional country hint ("IND" for India). Default renders US demo coords.
        state: Optional state/province hint (e.g., "TN" for Tamil Nadu when country=IND).
    """
    spots = _sample_critical_spots()

    # Override segment IDs/reasons with NH-coded entries for Tamil Nadu
    if country and country.lower() == "ind" and state and state.lower() in ["tn", "tamil nadu", "tamilnadu"]:
        tn_segments_meta = [
            {"segment_id": "NH44_TN_01", "reasons": ["Night rain + overspeed", "Container traffic spike"], "recommended_actions": ["Speed checks", "LED lighting"]},
            {"segment_id": "NH48_TN_02", "reasons": ["Fog near Krishnagiri ghat", "Sharp curves"], "recommended_actions": ["Fog beacons", "Rumble strips"]},
            {"segment_id": "NH32_TN_03", "reasons": ["Urban merge conflict (Chennai south)", "Peak congestion"], "recommended_actions": ["Dynamic signage", "Enforcement"]},
            {"segment_id": "NH38_TN_04", "reasons": ["Work zone near Trichy", "Lane shifts"], "recommended_actions": ["Cone taper", "Queue warning"]},
            {"segment_id": "NH544_TN_05", "reasons": ["Heavy rain near Coimbatore bypass", "Ponding risk"], "recommended_actions": ["Drainage check", "Speed advisory"]},
            {"segment_id": "NH83_TN_06", "reasons": ["Mixed traffic + bikes", "Evening peak"], "recommended_actions": ["Helmet checks", "Speed calming"]},
            {"segment_id": "NH45_TN_07", "reasons": ["Night crashes history", "Lighting gaps"], "recommended_actions": ["Lighting audit", "Patrol staging"]},
            {"segment_id": "NH66_TN_08", "reasons": ["Crosswind trucks", "Overtaking"], "recommended_actions": ["High-profile vehicle advisory", "Lane discipline"]},
        ]

        new_spots = []
        for i, base_spot in enumerate(spots[: len(tn_segments_meta)]):
            meta = tn_segments_meta[i]
            new_spots.append(CriticalSpot(
                segment_id=meta["segment_id"],
                road_name=base_spot.road_name,
                kilometers=base_spot.kilometers,
                risk_score=base_spot.risk_score,
                severity_label=base_spot.severity_label,
                reasons=meta["reasons"],
                recommended_actions=meta["recommended_actions"],
                color=base_spot.color,
                window=base_spot.window,
            ))
        spots = new_spots

    # Default: SF Bay demo pattern
    coords = [(37.7749 + (i * 0.02), -122.4194 + (i * 0.03)) for i in range(len(spots))]

    # India demo centered on Bengaluru
    if country and country.lower() == "ind":
        coords = [(12.9716 + (i * 0.02), 77.5946 + (i * 0.03)) for i in range(len(spots))]

    # Tamil Nadu sample cities (fixed meaningful coords)
    if country and country.lower() == "ind" and state and state.lower() in ["tn", "tamil nadu", "tamilnadu"]:
        tn_cities = [
            (13.0827, 80.2707),   # Chennai
            (11.0168, 76.9558),   # Coimbatore
            (9.9252, 78.1198),    # Madurai
            (10.7905, 78.7047),   # Tiruchirappalli
            (11.6643, 78.1460),   # Salem
            (8.7139, 77.7567),    # Tirunelveli
            (11.3410, 77.7172),   # Erode
            (12.9165, 79.1325),   # Vellore
        ]
        # If more spots than cities, repeat remainder with slight jitter
        coords = []
        for i, spot in enumerate(spots):
            base = tn_cities[i % len(tn_cities)]
            coords.append((base[0] + 0.01 * (i // len(tn_cities)), base[1] + 0.01 * (i // len(tn_cities))))

    segments = []
    for i, spot in enumerate(spots):
        lat, lng = coords[i]
        segments.append(MapSegment(
            segment_id=spot.segment_id,
            latitude=lat,
            longitude=lng,
            risk_score=spot.risk_score,
            color=spot.color,
            reasons=spot.reasons,
            recommended_actions=spot.recommended_actions,
        ))

    return MapReadyResponse(
        generated_at=datetime.now().isoformat(),
        projection="WGS84",
        segments=segments,
    )


# ============== Monthly Hotspot Report ==============


class MonthlyHotspot(BaseModel):
    """Monthly hotspot summary for planners."""
    segment_id: str
    road_name: str
    kilometers: str
    monthly_risk: float
    total_incidents: int
    serious_incidents: int
    fatal_incidents: int
    peak_hours: List[str]
    patterns: List[str]  # e.g., "weekends", "nighttime", "rain"
    long_term_actions: List[str]  # Infrastructure recommendations
    recommended_actions: List[str]


class MonthlyHotspotReport(BaseModel):
    """Monthly hotspot report stub."""
    month: str
    generated_at: str
    hotspots: List[MonthlyHotspot]


@router.get("/reports/hotspots/monthly", response_model=MonthlyHotspotReport)
async def monthly_hotspot_report(month: Optional[str] = None):
    """Provide a stub monthly hotspot report for planners."""
    month_label = month or datetime.now().strftime("%Y-%m")
    hotspots = [
        MonthlyHotspot(
            segment_id="S42",
            road_name="NH44_Hosur",
            kilometers="23-25 km",
            monthly_risk=0.88,
            total_incidents=12,
            serious_incidents=4,
            fatal_incidents=1,
            peak_hours=["07:00-09:00", "17:00-19:00"],
            patterns=["weekday peak hours", "rainy conditions", "high speed variance"],
            long_term_actions=["Install median barrier", "Upgrade lighting to LED", "Add rumble strips"],
            recommended_actions=["Nighttime lighting audit", "Speed harmonization"],
        ),
        MonthlyHotspot(
            segment_id="S18",
            road_name="NH44_Hosur",
            kilometers="18-20 km",
            monthly_risk=0.82,
            total_incidents=9,
            serious_incidents=3,
            fatal_incidents=0,
            peak_hours=["06:00-08:00", "16:00-18:00"],
            patterns=["early morning fog", "weekday evenings"],
            long_term_actions=["Install fog beacons", "Improve drainage", "Strengthen guardrails"],
            recommended_actions=["Fog sensor calibration", "Add rumble strips"],
        ),
        MonthlyHotspot(
            segment_id="S7",
            road_name="NH44_Hosur",
            kilometers="7-9 km",
            monthly_risk=0.75,
            total_incidents=7,
            serious_incidents=2,
            fatal_incidents=0,
            peak_hours=["15:00-18:00"],
            patterns=["afternoon congestion", "work zone impacts"],
            long_term_actions=["Temporary work zone review", "Queue detection system"],
            recommended_actions=["Work zone timing review", "Queue warning study"],
        ),
    ]
    return MonthlyHotspotReport(
        month=month_label,
        generated_at=datetime.now().isoformat(),
        hotspots=hotspots,
    )


# ============== CSV Export ==============

from fastapi.responses import StreamingResponse
import csv
import io


@router.get("/reports/hotspots/monthly/export")
async def export_monthly_hotspots_csv(month: Optional[str] = None):
    """Export monthly hotspot report as CSV for spreadsheet/GIS tools."""
    report = await monthly_hotspot_report(month)
    
    output = io.StringIO()
    writer = csv.writer(output)
    
    # Write header
    writer.writerow([
        "Segment ID", "Road Name", "Kilometers", "Monthly Risk", "Total Incidents",
        "Serious Incidents", "Fatal Incidents", "Peak Hours", "Patterns", "Long-term Actions"
    ])
    
    # Write data rows
    for hotspot in report.hotspots:
        writer.writerow([
            hotspot.segment_id,
            hotspot.road_name,
            hotspot.kilometers,
            f"{hotspot.monthly_risk:.2f}",
            hotspot.total_incidents,
            hotspot.serious_incidents,
            hotspot.fatal_incidents,
            "; ".join(hotspot.peak_hours),
            "; ".join(hotspot.patterns),
            "; ".join(hotspot.long_term_actions),
        ])
    
    output.seek(0)
    return StreamingResponse(
        iter([output.getvalue()]),
        media_type="text/csv",
        headers={"Content-Disposition": f"attachment; filename=hotspots_{report.month}.csv"}
    )


@router.get("/reports/critical-spots/export")
async def export_critical_spots_csv():
    """Export top-10 critical spots as CSV for police/operators."""
    report = await get_critical_spots()
    
    output = io.StringIO()
    writer = csv.writer(output)
    
    # Write header
    writer.writerow([
        "Rank", "Segment ID", "Road Name", "Kilometers", "Risk Score", "Severity",
        "Reasons", "Recommended Actions", "Window"
    ])
    
    # Write data rows
    for rank, spot in enumerate(report.spots[:10], 1):
        writer.writerow([
            rank,
            spot.segment_id,
            spot.road_name,
            spot.kilometers,
            f"{spot.risk_score:.2f}",
            spot.severity_label,
            "; ".join(spot.reasons),
            "; ".join(spot.recommended_actions),
            spot.window,
        ])
    
    output.seek(0)
    return StreamingResponse(
        iter([output.getvalue()]),
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=critical_spots_tonight.csv"}
    )

# ============== 1. HOTSPOT & PATROL PLANNING SERVICE ==============

class HotspotSegment(BaseModel):
    """A high-risk segment for patrol focus."""
    segment_id: str
    road_name: str
    risk_level: Literal["LOW", "MEDIUM", "HIGH"]
    reason_summary: str
    suggested_enforcement: str


class HotspotRequest(BaseModel):
    """Request for hotspot patrol planning."""
    date: str = Field(..., description="Date (e.g., '2026-01-06')")
    time_window: str = Field(..., description="Time window (e.g., '18:00-23:00')")
    district: Optional[str] = None


class HotspotResponse(BaseModel):
    """Response with top hotspots for patrol planning."""
    hotspots: List[HotspotSegment]
    window: str
    region: Optional[str] = None


@router.post("/hotspots/today", response_model=HotspotResponse)
async def get_hotspots_today(request: HotspotRequest):
    """Get top hotspots for patrol planning today.
    
    Args:
        request: Hotspot request with date, time window, and optional district
    
    Returns:
        Top N high-risk segments with enforcement suggestions
    """
    # Demo data: top segments for this time window
    hotspots = [
        HotspotSegment(
            segment_id="S42",
            road_name="NH44 Hosur Bypass",
            risk_level="HIGH",
            reason_summary="Night traffic + wet road conditions + speed violations",
            suggested_enforcement="Speed checks, high-visibility patrol"
        ),
        HotspotSegment(
            segment_id="S15",
            road_name="Varthur Main Road",
            risk_level="HIGH",
            reason_summary="Heavy congestion + junction accident history",
            suggested_enforcement="Traffic management checkpoint, camera monitoring"
        ),
        HotspotSegment(
            segment_id="S28",
            road_name="ORR Outer Ring Road",
            risk_level="MEDIUM",
            reason_summary="Speed spike detected in last hour",
            suggested_enforcement="Routine patrol presence"
        ),
        HotspotSegment(
            segment_id="S51",
            road_name="Sarjapur Main Road",
            risk_level="MEDIUM",
            reason_summary="Pedestrian crossing zone + poor visibility",
            suggested_enforcement="Pedestrian safety checkpoint"
        ),
        HotspotSegment(
            segment_id="S33",
            road_name="Electronic City Road",
            risk_level="LOW",
            reason_summary="Baseline patrol area",
            suggested_enforcement="Regular monitoring"
        ),
    ]
    
    return HotspotResponse(
        hotspots=hotspots,
        window=f"{request.date} {request.time_window}",
        region=request.district
    )


# ============== 2. ROUTE SAFETY & TRIP PLANNING SERVICE ==============

class RouteSafetyRequest(BaseModel):
    """Request for route safety evaluation."""
    origin: str
    destination: str
    departure_time: str


class RouteOption(BaseModel):
    """A candidate route with safety scoring."""
    route_id: str
    name: str
    distance_km: float
    estimated_time_min: int
    safety_score: int
    safety_label: Literal["SAFE", "MODERATE", "RISKY"]
    highest_risk_segment: str
    advice: str


class RouteSafetyResponse(BaseModel):
    """Routes ranked by safety."""
    origin: str
    destination: str
    departure_time: str
    routes: List[RouteOption]


@router.post("/route/safety-score", response_model=RouteSafetyResponse)
async def evaluate_route_safety(request: RouteSafetyRequest):
    """Evaluate safety of candidate routes.
    
    Args:
        request: Origin, destination, departure time
    
    Returns:
        Routes ranked by safety score with risk segments highlighted
    """
    routes = [
        RouteOption(
            route_id="A",
            name="Route A - Via NH44 Direct",
            distance_km=45,
            estimated_time_min=55,
            safety_score=72,
            safety_label="MODERATE",
            highest_risk_segment="S42 (HIGH)",
            advice="Direct route, but S42 is HIGH risk at night"
        ),
        RouteOption(
            route_id="B",
            name="Route B - Via ORR Bypass",
            distance_km=48,
            estimated_time_min=62,
            safety_score=85,
            safety_label="SAFE",
            highest_risk_segment="S28 (MEDIUM)",
            advice="5 minutes longer but significantly safer - recommended for night travel"
        ),
        RouteOption(
            route_id="C",
            name="Route C - Via Electronic City",
            distance_km=52,
            estimated_time_min=68,
            safety_score=78,
            safety_label="MODERATE",
            highest_risk_segment="S51 (MEDIUM)",
            advice="Longest route, moderate safety due to pedestrian zones"
        ),
    ]
    
    return RouteSafetyResponse(
        origin=request.origin,
        destination=request.destination,
        departure_time=request.departure_time,
        routes=routes
    )


# ============== 3. MONTHLY HOTSPOT & POLICY REPORT SERVICE ==============

class HotspotEntry(BaseModel):
    """Monthly hotspot with accident statistics."""
    rank: int
    segment_id: str
    road_name: str
    total_crashes: int
    serious_injuries: int
    fatal_crashes: int
    average_risk_score: float
    peak_hours: str
    main_factors: List[str]
    recommended_interventions: List[str]


class MonthlyReportRequest(BaseModel):
    """Request for monthly hotspot report."""
    month: str = Field(..., description="Month (e.g., '2026-01')")
    region: Optional[str] = None


class MonthlyReportResponse(BaseModel):
    """Planner-friendly monthly report."""
    month: str
    region: Optional[str] = None
    total_crashes_reported: int
    serious_incidents: int
    fatal_incidents: int
    hotspots: List[HotspotEntry]
    summary_insights: List[str]


@router.post("/reports/hotspots/monthly", response_model=MonthlyReportResponse)
async def get_monthly_hotspot_report(request: MonthlyReportRequest):
    """Get monthly hotspot report for planning.
    
    Args:
        request: Monthly report request with month and optional region
    
    Returns:
        Comprehensive monthly report with hotspots and policy recommendations
    """
    hotspots = [
        HotspotEntry(
            rank=1,
            segment_id="S42",
            road_name="NH44 Hosur Bypass",
            total_crashes=12,
            serious_injuries=8,
            fatal_crashes=1,
            average_risk_score=0.78,
            peak_hours="18:00-23:00",
            main_factors=["Night driving + wet roads", "High speed + congestion", "Poor lighting"],
            recommended_interventions=["Install LED street lights", "Speed reduction cameras", "Enhanced road markings"]
        ),
        HotspotEntry(
            rank=2,
            segment_id="S15",
            road_name="Varthur Main Road",
            total_crashes=9,
            serious_injuries=5,
            fatal_crashes=0,
            average_risk_score=0.65,
            peak_hours="08:00-10:00, 17:00-19:00",
            main_factors=["Junction design", "Heavy congestion", "Pedestrian crossing"],
            recommended_interventions=["Redesign junction", "Install traffic signal optimization", "Pedestrian overpass"]
        ),
        HotspotEntry(
            rank=3,
            segment_id="S28",
            road_name="ORR Outer Ring Road",
            total_crashes=7,
            serious_injuries=3,
            fatal_crashes=0,
            average_risk_score=0.55,
            peak_hours="22:00-02:00",
            main_factors=["Speed violations", "Night driving", "Lack of barriers"],
            recommended_interventions=["Install median barriers", "Speed enforcement cameras", "Improved signage"]
        ),
    ]
    
    return MonthlyReportResponse(
        month=request.month,
        region=request.region,
        total_crashes_reported=28,
        serious_incidents=16,
        fatal_incidents=1,
        hotspots=hotspots,
        summary_insights=[
            "Night-time accidents are 3x more frequent - prioritize lighting improvements",
            "Junctions account for 45% of serious incidents - intersection redesigns recommended",
            "Weather-related crashes spike during monsoon - consider seasonal enforcement escalation"
        ]
    )


# ============== 4. ALERT & NOTIFICATION SERVICE ==============

class AlertRule(BaseModel):
    """A subscription rule for risk alerts."""
    rule_name: str
    radius_km: int
    risk_threshold: Literal["LOW", "MEDIUM", "HIGH"]
    notification_channel: Literal["webhook", "email", "sms", "in-app"]
    time_window_min: int


class AlertSubscriptionRequest(BaseModel):
    """Request to subscribe to risk alerts."""
    center_location: str
    rule: AlertRule


class AlertSubscriptionResponse(BaseModel):
    """Confirmation of alert subscription."""
    subscription_id: str
    center_location: str
    rule_name: str
    status: str
    message: str


@router.post("/alerts/subscribe", response_model=AlertSubscriptionResponse)
async def subscribe_to_alerts(request: AlertSubscriptionRequest):
    """Subscribe to risk alerts for a region.
    
    Args:
        request: Location and alert rule details
    
    Returns:
        Subscription confirmation with ID
    """
    import uuid
    subscription_id = str(uuid.uuid4())[:8]
    
    return AlertSubscriptionResponse(
        subscription_id=subscription_id,
        center_location=request.center_location,
        rule_name=request.rule.rule_name,
        status="ACTIVE",
        message=f"Alert subscription created. You will receive {request.rule.notification_channel} notifications when {request.rule.risk_threshold} risk is detected within {request.rule.radius_km}km of {request.center_location}."
    )


class AlertNotification(BaseModel):
    """An alert notification sent to subscriber."""
    subscription_id: str
    timestamp: str
    segment_id: str
    risk_level: str
    explanation: str
    suggested_action: str


@router.get("/alerts/sample", response_model=AlertNotification)
async def get_sample_alert():
    """Get a sample alert notification (for demo)."""
    return AlertNotification(
        subscription_id="sub_abc123",
        timestamp="2026-01-06T20:15:00Z",
        segment_id="S42",
        risk_level="HIGH",
        explanation="Sudden heavy rainfall detected + speed spike observed on NH44 Hosur. Accident risk increased to HIGH for next 30 minutes.",
        suggested_action="Dispatch additional patrol units. Consider speed limit reduction notifications."
    )
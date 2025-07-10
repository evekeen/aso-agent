import json
from dataclasses import dataclass
from datetime import datetime
from typing import List, Optional
from urllib.parse import quote_plus

import aiohttp


@dataclass
class AppstoreApp:
    app_id: str
    title: str
    url: str
    artist_name: str
    bundle_id: str
    genres: List[str]
    rating: Optional[float] = None
    rating_count: Optional[int] = None
    release_date: Optional[datetime] = None
    icon_url: Optional[str] = None
    subtitle: Optional[str] = None
    
    def __repr__(self):
        return f"AppstoreApp(title='{self.title}', app_id='{self.app_id}', artist='{self.artist_name}')"    


class AppStoreMarkets:
    """
    App Store store IDs per country

    Borrowed from https://github.com/facundoolano/app-store-scraper.
    """
    DZ = 143563
    AO = 143564
    AI = 143538
    AR = 143505
    AM = 143524
    AU = 143460
    AT = 143445
    AZ = 143568
    BH = 143559
    BB = 143541
    BY = 143565
    BE = 143446
    BZ = 143555
    BM = 143542
    BO = 143556
    BW = 143525
    BR = 143503
    VG = 143543
    BN = 143560
    BG = 143526
    CA = 143455
    KY = 143544
    CL = 143483
    CN = 143465
    CO = 143501
    CR = 143495
    HR = 143494
    CY = 143557
    CZ = 143489
    DK = 143458
    DM = 143545
    EC = 143509
    EG = 143516
    SV = 143506
    EE = 143518
    FI = 143447
    FR = 143442
    DE = 143443
    GB = 143444
    GH = 143573
    GR = 143448
    GD = 143546
    GT = 143504
    GY = 143553
    HN = 143510
    HK = 143463
    HU = 143482
    IS = 143558
    IN = 143467
    ID = 143476
    IE = 143449
    IL = 143491
    IT = 143450
    JM = 143511
    JP = 143462
    JO = 143528
    KE = 143529
    KW = 143493
    LV = 143519
    LB = 143497
    LT = 143520
    LU = 143451
    MO = 143515
    MK = 143530
    MG = 143531
    MY = 143473
    ML = 143532
    MT = 143521
    MU = 143533
    MX = 143468
    MS = 143547
    NP = 143484
    NL = 143452
    NZ = 143461
    NI = 143512
    NE = 143534
    NG = 143561
    NO = 143457
    OM = 143562
    PK = 143477
    PA = 143485
    PY = 143513
    PE = 143507
    PH = 143474
    PL = 143478
    PT = 143453
    QA = 143498
    RO = 143487
    RU = 143469
    SA = 143479
    SN = 143535
    SG = 143464
    SK = 143496
    SI = 143499
    ZA = 143472
    ES = 143454
    LK = 143486
    SR = 143554
    SE = 143456
    CH = 143459
    TW = 143470
    TZ = 143572
    TH = 143475
    TN = 143536
    TR = 143480
    UG = 143537
    UA = 143492
    AE = 143481
    US = 143441
    UY = 143514
    UZ = 143566
    VE = 143502
    VN = 143471
    YE = 143571


class AppStoreException(Exception):
    """
    Thrown when an error occurs in the App Store scraper
    """
    pass


COUNTRIES = [
    'ad', # Andorra
    'at', # Austria
    'be', # Belgium
    'ca', # Canada
    'ch', # Switzerland
    'cy', # Cyprus
    'cz', # Czechia
    'de', # Germany
    'dk', # Denmark
    'ee', # Estonia
    'es', # Spain
    'fi', # Finland
    'fr', # France
    'gb', # Great Britain
    'gi', # Gibraltar
    'gr', # Greece
    'hr', # Hungary
    'ie', # Ireland
    'im', # Isle of Man
    'is', # Iceland
    'it', # Italy
    'lu', # Luxembourg
    'lv', # Latvia
    'mc', # Monaco
    'me', # Montenegro
    'mt', # Malta
    'nl', # Netherlands
    'no', # Norway
    'pl', # Poland
    'pt', # Portugal
    'ro', # Romania
    'rs', # Serbia
    'se', # Sweden
    'si', # Slovenia
    'sk', # Slovakia
    'sr', # ???
    'tr', # Turkey
    'ua', # Ukraine
    'us', # United States of America
]


class AppStoreScraper:
    """Async App Store scraper for retrieving app information"""
    
    def __init__(self):
        self.session: Optional[aiohttp.ClientSession] = None
    
    async def __aenter__(self):
        self.session = aiohttp.ClientSession()
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self.session:
            await self.session.close()
    
    def get_store_id_for_country(self, country: str) -> int:
        """
        Get store ID for country code

        :param str country:  Two-letter country code for the store to search in.
        """
        country = country.upper()

        if hasattr(AppStoreMarkets, country):
            return getattr(AppStoreMarkets, country)
        else:
            raise AppStoreException(f"Country code not found for {country}")
    
    async def get_app_ids_for_query(
        self, 
        term: str, 
        num: int = 5, 
        page: int = 1, 
        country: str = "us", 
        lang: str = "nl"
    ) -> List[str]:
        """
        Retrieve suggested app IDs for search query

        :param str term:  Search query
        :param int num:  Amount of items to return per page, default 5
        :param int page:  Amount of pages to return
        :param str country:  Two-letter country code of store to search in
        :param str lang:  Language code to search with, default 'en_US'

        :return list:  List of App IDs returned for search query
        """
        if not term:
            raise AppStoreException("No term was given")

        url = "https://search.itunes.apple.com/WebObjects/MZStore.woa/wa/search?clientApplication=Software&media=software&term="
        url += quote_plus(term)

        amount = int(num) * int(page)

        country_id = self.get_store_id_for_country(country)
        headers = {
            "X-Apple-Store-Front": f"{country_id},24 t:native",
            "Accept-Language": lang
        }

        if not self.session:
            self.session = aiohttp.ClientSession()

        try:
            async with self.session.get(url, headers=headers) as response:
                if response.status != 200:
                    raise AppStoreException(f"HTTP {response.status}: {await response.text()}")
                
                result = await response.json()
        except aiohttp.ClientError as ce:
            raise AppStoreException(f"Cannot connect to store: {ce}")
        except json.JSONDecodeError:
            raise AppStoreException("Could not parse app store response")
        

        if "bubbles" not in result or not result["bubbles"]:
            raise AppStoreException(f"No results found for search term {term} (country {country}, lang {lang})")

        return [app["id"] for app in result["bubbles"][0]["results"][:amount]]


    async def get_apps_for_query(
        self, 
        term: str, 
        num: int = 5, 
        page: int = 1, 
        country: str = "us", 
        lang: str = "en"
    ) -> List[AppstoreApp]:
        """
        Retrieve app details for search query

        :param str term:  Search query
        :param int num:  Amount of items to return per page, default 5
        :param int page:  Amount of pages to return
        :param str country:  Two-letter country code of store to search in
        :param str lang:  Language code to search with, default 'en'

        :return list:  List of AppstoreApp objects
        """
        if not term:
            raise AppStoreException("No term was given")

        url = "https://search.itunes.apple.com/WebObjects/MZStore.woa/wa/search?clientApplication=Software&media=software&term="
        url += quote_plus(term)

        amount = int(num) * int(page)

        country_id = self.get_store_id_for_country(country)
        headers = {
            "X-Apple-Store-Front": f"{country_id},24 t:native",
            "Accept-Language": lang
        }

        if not self.session:
            self.session = aiohttp.ClientSession()

        try:
            async with self.session.get(url, headers=headers) as response:
                if response.status != 200:
                    raise AppStoreException(f"HTTP {response.status}: {await response.text()}")
                
                result = await response.json()
        except aiohttp.ClientError as ce:
            raise AppStoreException(f"Cannot connect to store: {ce}")
        except json.JSONDecodeError:
            raise AppStoreException("Could not parse app store response")

        if "bubbles" not in result or not result["bubbles"]:
            raise AppStoreException(f"No results found for search term {term} (country {country}, lang {lang})")

        # Get app IDs from bubbles
        app_ids = [app["id"] for app in result["bubbles"][0]["results"][:amount]]
        
        # Get detailed app data
        apps = []
        if "storePlatformData" in result and "native-search-lockup-search" in result["storePlatformData"]:
            app_data = result["storePlatformData"]["native-search-lockup-search"]["results"]
            
            for app_id in app_ids:
                if str(app_id) in app_data:
                    app_info = app_data[str(app_id)]
                    
                    # Parse release date
                    release_date = None
                    if "releaseDate" in app_info:
                        try:
                            release_date = datetime.fromisoformat(app_info["releaseDate"].replace("Z", "+00:00"))
                        except:
                            pass
                    
                    # Get icon URL (use the 170x170 version)
                    icon_url = None
                    if "artwork" in app_info and app_info["artwork"]:
                        icon_url = app_info["artwork"][0].get("url")
                    
                    # Get rating info
                    rating = None
                    rating_count = None
                    if "userRating" in app_info:
                        rating = app_info["userRating"].get("value")
                        rating_count = app_info["userRating"].get("ratingCount")
                    
                    app = AppstoreApp(
                        app_id=str(app_id),
                        title=app_info.get("name", ""),
                        url=app_info.get("url", ""),
                        artist_name=app_info.get("artistName", ""),
                        bundle_id=app_info.get("bundleId", ""),
                        genres=app_info.get("genreNames", []),
                        rating=rating,
                        rating_count=rating_count,
                        release_date=release_date,
                        icon_url=icon_url,
                        subtitle=app_info.get("subtitle")
                    )
                    apps.append(app)
        
        return apps


async def search_app_store(term: str, country: str = "us", num: int = 5) -> List[AppstoreApp]:
    """
    Convenience function to search the App Store and get app details
    
    :param term: Search query
    :param country: Two-letter country code
    :param num: Number of results to return
    :return: List of AppstoreApp objects
    """
    async with AppStoreScraper() as scraper:
        return await scraper.get_apps_for_query(term, num=num, country=country)
import asyncio
import random
from datetime import datetime, timedelta
import uuid
from sqlalchemy import select

from database.setup import async_session_maker
from models.user import User
from models.event import Event
from models.oauth import OAuthAccount 

# === KONFIGURACJA ===
ILOSC_WYDARZEN = 50

# Granice Wielkopolski
LAT_MIN = 51.45
LAT_MAX = 53.60
LNG_MIN = 15.75
LNG_MAX = 19.10

PREFIXES = ["Nocne", "Wielkie", "Sąsiedzkie", "Otwarte", "Charytatywne", "Turniejowe"]
TOPICS = ["Granie w RPG", "Ognisko", "Warsztaty Jogi", "Kodowanie w Pythonie", 
          "Zawody Pływackie", "Spotkanie D&D", "Degustacja Pizzy", "Targi Staroci", 
          "Karaoke", "Bieganie po lesie"]
CITIES = ["Poznań", "Kalisz", "Konin", "Leszno", "Piła", "Gniezno", "Ostrów Wlkp."]

DESCRIPTIONS = [
    "Zapraszamy wszystkich chętnych! Będzie super zabawa i darmowe przekąski.",
    "Wymagane własne obuwie i dobry humor. Zaczynamy punktualnie.",
    "Spotkanie dla pasjonatów i amatorów. Poziom zaawansowania dowolny.",
    "Wstęp wolny, ale liczba miejsc ograniczona. Kto pierwszy ten lepszy!",
    "To będzie niezapomniane wydarzenie. Nie może Cię zabraknąć."
]

def random_date(start_year=2026, end_year=2027):
    start = datetime(start_year, 1, 1)
    end = datetime(end_year, 1, 1)
    delta = end - start
    random_seconds = random.randrange(int(delta.total_seconds()))
    return start + timedelta(seconds=random_seconds)

def random_coords():
    lat = random.uniform(LAT_MIN, LAT_MAX)
    lng = random.uniform(LNG_MIN, LNG_MAX)
    return lat, lng

async def main():
    print("--- ROZPOCZYNAM GENEROWANIE DANYCH TESTOWYCH ---")
    
    async with async_session_maker() as session:
        result = await session.execute(select(User))
        user = result.scalars().first()
        
        if not user:
            print("!!! BŁĄD: W bazie nie ma żadnego użytkownika !!!")
            print("Zarejestruj najpierw konto przez stronę, żebyśmy mieli kogo wpisać jako twórcę.")
            return

        print(f"Znaleziono użytkownika: {user.email} (ID: {user.id})")
        print(f"Tworzę {ILOSC_WYDARZEN} wydarzeń...")

        events_list = []
        for i in range(ILOSC_WYDARZEN):
            lat, lng = random_coords()
            
            title = f"{random.choice(PREFIXES)} {random.choice(TOPICS)}"
            if random.random() > 0.7:
                title += f" - {random.choice(CITIES)}"
            
            event_date = random_date()
            
            new_event = Event(
                title=title,
                description=random.choice(DESCRIPTIONS),
                event_date=event_date,
                latitude=lat,
                longitude=lng,
                is_deleted=False,
                creator_id=user.id
            )
            events_list.append(new_event)
        
        session.add_all(events_list)
        await session.commit()
        
        print("--- SUKCES! DODANO WYDARZENIA ---")
        print(f"Lokalizacja: Wielkopolska")
        print(f"Zakres dat: 2026-2027")

if __name__ == "__main__":
    asyncio.run(main())
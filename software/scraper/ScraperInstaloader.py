import instaloader

# Inicializace Instaloaderu
L = instaloader.Instaloader()

# Zadej Instagram uživatelské jméno

profile_name = "tom_hromek"  

try:
    profile = instaloader.Profile.from_username(L.context, profile_name)

    print(f"📸 Profil: {profile.full_name}")
    print(f"👥 Sledující: {profile.followers}")
    print(f"🎯 Sleduje: {profile.followees}")
    print(f"📝 Bio: {profile.biography}")
    print(f"🔗 Odkaz v bio: {profile.external_url}")

except Exception as e:
    print(f"❌ Chyba při získávání profilu: {e}")

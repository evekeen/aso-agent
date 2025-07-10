import asyncio
from lib.appstore import search_app_store, AppStoreScraper, AppstoreApp


async def test_search():
    print("Testing App Store search...")
    
    # Test 1: Search for a popular app
    print("\n1. Searching for 'Instagram':")
    try:
        results = await search_app_store("Instagram", country="us", num=3)
        print(f"   Found {len(results)} apps:")
        for app in results:
            print(f"   - {app.title} (ID: {app.app_id}) by {app.artist_name}")
        assert isinstance(results, list)
        assert len(results) <= 3
        assert all(isinstance(app, AppstoreApp) for app in results)
        assert all(isinstance(app.app_id, str) for app in results)
        print("   ✓ Test passed")
    except Exception as e:
        print(f"   ✗ Error: {e}")
    
    # Test 2: Search with different country
    print("\n2. Searching for 'WhatsApp' in Germany:")
    try:
        async with AppStoreScraper() as scraper:
            results = await scraper.get_apps_for_query("WhatsApp", num=2, country="de")
            print(f"   Found {len(results)} apps:")
            for app in results:
                print(f"   - {app.title} (Bundle: {app.bundle_id})")
            assert isinstance(results, list)
            assert len(results) <= 2
            assert all(isinstance(app, AppstoreApp) for app in results)
            print("   ✓ Test passed")
    except Exception as e:
        print(f"   ✗ Error: {e}")
    
    # Test 3: Search for games
    print("\n3. Searching for 'Minecraft':")
    try:
        results = await search_app_store("Minecraft", num=2)
        print(f"   Found {len(results)} apps:")
        for app in results:
            print(f"   - {app.title} - Rating: {app.rating}⭐ ({app.rating_count:,} reviews)" if app.rating else f"   - {app.title}")
        assert isinstance(results, list)
        assert len(results) <= 2
        assert all(isinstance(app, AppstoreApp) for app in results)
        print("   ✓ Test passed")
    except Exception as e:
        print(f"   ✗ Error: {e}")
    
    print("\n✅ All tests completed!")


if __name__ == "__main__":
    asyncio.run(test_search())
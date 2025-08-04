"""Entry point for the weather integration."""

from uc_intg_weather.driver import main, loop

if __name__ == "__main__":
    try:
        loop.run_until_complete(main())
        loop.run_forever()
    except KeyboardInterrupt:
        print("Driver stopped by user.")
    finally:
        loop.close()
import argparse
import logging
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager
import time
from urllib.parse import urlencode
from tenacity import retry, stop_after_attempt, wait_exponential
from mylog import setup_logger
from email_utils import send_html_email
from datetime import datetime
import uuid
import os
from dotenv import load_dotenv


logging.getLogger("WDM").setLevel(logging.ERROR)
logging.getLogger("urllib3").setLevel(logging.ERROR)

logger = setup_logger(
    name="opora_checker", log_file="/Users/dorbourshan/Documents/availability.log"
)
load_dotenv(dotenv_path=r'/Users/dorbourshan/Documents/BOOKING.env')
email_user = os.getenv("EMAIL_USER")
email_password = os.getenv("EMAIL_PASSWORD")
recipients_str = os.getenv("EMAIL_RECIPIENTS", "")
recipients = [email.strip() for email in recipients_str.split(",") if email.strip()]

def get_driver():
    """Initialize and return a headless Chrome WebDriver."""
    options = Options()
    options.add_argument("--headless")
    options.add_argument("--disable-gpu")
    options.add_argument("--no-sandbox")
    options.add_argument("--window-size=1920,1080")
    options.add_argument(
        "user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/116.0.0.0 Safari/537.36"
    )
    service = Service(ChromeDriverManager().install())
    return webdriver.Chrome(service=service, options=options)


@retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=4, max=10))
def check_availability(
    driver, url, checkin="2025-09-30", nights=2, adults=2, rooms=1, max_price=None
):
    """
    Check if rooms are available by submitting the search form and extracting names and prices of available rooms.

    Args:
        driver: Selenium WebDriver instance.
        url: The URL of the booking page.
        checkin: Check-in date (format: YYYY-MM-DD).
        nights: Number of nights.
        adults: Number of adults.
        rooms: Number of rooms.
        max_price: Maximum price threshold (optional).

    Returns:
        A list of dictionaries containing the name and price of available rooms.
    """
    try:
        driver.get(url)
        wait = WebDriverWait(driver, 30)

        # Ensure DOM is fully loaded
        wait.until(
            lambda d: d.execute_script("return document.readyState") == "complete"
        )
        logger.debug("DOM fully loaded")

        # Check if results table is already loaded
        try:
            wait.until(
                EC.presence_of_element_located((By.CSS_SELECTOR, "table.data.rmtbl"))
            )
            logger.debug("Results table already loaded, skipping form submission")
        except:
            # Set form inputs
            try:
                checkin_input = wait.until(
                    EC.presence_of_element_located((By.ID, "date-input-fromd"))
                )
                checkin_input.clear()
                checkin_input.send_keys(checkin)
                logger.debug(f"Set check-in date to: {checkin}")

                nights_select = wait.until(
                    EC.presence_of_element_located((By.ID, "select-nights"))
                )
                driver.execute_script(
                    f"arguments[0].value = '{nights}';", nights_select
                )
                logger.debug(f"Set nights to: {nights}")

                adults_select = wait.until(
                    EC.presence_of_element_located((By.ID, "select-adults"))
                )
                driver.execute_script(
                    f"arguments[0].value = '{adults}';", adults_select
                )
                logger.debug(f"Set adults to: {adults}")

                # Click the Search button
                search_button = wait.until(
                    EC.element_to_be_clickable(
                        (By.CSS_SELECTOR, "button.prime[type='submit']")
                    )
                )
                logger.debug(
                    f"Search button HTML: {search_button.get_attribute('outerHTML')}"
                )
                search_button.click()
                logger.debug("Clicked Search button to load results")
                time.sleep(5)  # Increased delay for results to load
            except Exception as e:
                logger.warning(f"Could not submit search form: {e}")

        wait.until(
            EC.presence_of_element_located((By.CSS_SELECTOR, "table.data.rmtbl"))
        )
        logger.debug("Results table loaded")

        # Find all Book Now buttons
        buttons = wait.until(
            EC.presence_of_all_elements_located(
                (By.XPATH, "//button[starts-with(@id, 'rate-btn-')]")
            )
        )
        logger.debug(f"Found {len(buttons)} 'Book Now' buttons")

        # Save page source for debugging
        # with open(
        #     "/Users/dorbourshan/Documents/page_source.html", "w", encoding="utf-8"
        # ) as file:
        #     file.write(driver.page_source)
        # logger.info("✅ Saved page source to 'page_source.html'")

        available_rooms = []
        for i, button in enumerate(buttons):
            logger.debug(
                f"Button {i+1} HTML: {button.get_attribute('outerHTML')[:200]}..."
            )
            if button.is_enabled() and "Book Now" in button.text:
                try:
                    # Find the parent <tr> with a fallback
                    parent_row = button.find_element(
                        By.XPATH,
                        "./ancestor::tr[contains(@class, 'solo') or @data-rate]",
                    )
                    logger.debug(
                        f"Button {i+1} parent row HTML: {parent_row.get_attribute('outerHTML')[:300]}..."
                    )

                    # Check if the row is available (data-status="AVL")
                    status = parent_row.get_attribute("data-status")
                    logger.debug(f"Button {i+1} status: {status}")
                    if status != "AVL":
                        logger.debug(
                            f"Button {i+1}: Skipping non-available room (status: {status})"
                        )
                        continue

                    # Find the preceding <tr class="room"> for the room name
                    room_name_element = parent_row.find_element(
                        By.XPATH,
                        "./preceding-sibling::tr[@class='room']//td[@class='name']",
                    )
                    room_name = room_name_element.text.strip()
                    logger.debug(f"Button {i+1} room name: {room_name}")

                    # Extract and clean price from <td class="price"><div class="val">
                    price_elements = parent_row.find_elements(
                        By.XPATH, ".//td[@class='price']//div[@class='val']"
                    )
                    logger.debug(
                        f"Button {i+1} price elements: {[elem.text.strip() for elem in price_elements if elem.text.strip()]}"
                    )
                    price = None
                    for elem in price_elements:
                        price_text = (
                            elem.text.strip().replace("₪", "").replace(",", "").strip()
                        )
                        if price_text:
                            price = float(price_text)
                            break  # Take the first valid price

                    if price is None:
                        logger.warning(
                            f"Button {i+1}: Could not extract price for room: {room_name}"
                        )
                        continue

                    # Apply max_price filter
                    if max_price and price > max_price:
                        logger.debug(
                            f"Button {i+1}: Skipping room {room_name} with price {price} ILS (exceeds max_price {max_price})"
                        )
                        continue

                    # Add to the list of available rooms
                    available_rooms.append({"name": room_name, "price": price})
                    logger.debug(
                        f"Button {i+1}: Added room: {room_name}, Price: {price} ILS"
                    )
                except Exception as e:
                    logger.warning(
                        f"Button {i+1}: Could not extract details for a room: {e}"
                    )
                    continue

        if available_rooms:
            logger.info(f"✅ Found {len(available_rooms)} available room(s):")
            for room in available_rooms:
                logger.info(f"Room: {room['name']}, Price: {room['price']} ILS")
        else:
            logger.info("❌ No available rooms found.")
        return available_rooms

    except Exception as e:
        logger.error(f"Error checking availability: {e}")
        raise


def send_email(rooms, max_price=1500):
    html_content = generate_email_html(rooms=rooms, max_price=max_price)
    send_html_email(
        subject="Opora Country Living - Room Availability Update",
        html_content=html_content,
        from_addr=email_user,
        to_addrs=recipients,
        login_user=email_user,
        login_password=email_password,
    )


def generate_email_html(rooms, max_price: float):
    room_rows = ""
    rows_added = 0

    for room in sorted(rooms, key=lambda x: x.get("price", 0)):  # Sort by price
        name = room.get("name", "Unknown")
        price = room.get("price", 0)
        if price < max_price:
            room_rows += f"""
            <tr>
              <td style="border: 1px solid #d1d5db; padding: 12px; text-align: left; background-color: #ffffff; font-size: 13px; color: #374151;">{name}</td>
              <td style="border: 1px solid #d1d5db; padding: 12px; text-align: left; font-weight: 600; color: #15803d; font-size: 13px;">{price:.2f}</td>
            </tr>
            """
            rows_added += 1

    if rows_added == 0:
        room_rows = """
        <tr>
          <td colspan="2" style="border: 1px solid #d1d5db; padding: 12px; text-align: center; background-color: #ffffff; font-size: 13px; color: #374151;">No rooms available under 1500 ILS.</td>
        </tr>
        """

    try:
        with open("email_template.html", "r") as file:
            html_template = file.read()
    except FileNotFoundError:
        logger.error("email_template.html not found")
        raise

    # Replace placeholders
    current_date = datetime.now().strftime("%B %d, %Y %I:%M %p %Z")
    scan_id = str(uuid.uuid4())[:8]
    return (
        html_template.replace("{{ROOM_ROWS}}", room_rows)
        .replace("{{CURRENT_DATE}}", current_date)
        .replace("{{ROOM_COUNT}}", str(rows_added))
        .replace("{{SCAN_ID}}", scan_id)
        .replace('{{MAX_PRICE}}', f"{max_price:.2f}")
    )


def main():
    """Main function to parse arguments and check availability."""
    parser = argparse.ArgumentParser(
        description="Check availability for Opora Country Living"
    )
    parser.add_argument(
        "--checkin",
        default="2025-09-30",
        help="Check-in date (YYYY-MM-DD, default: 2025-09-30)",
    )
    parser.add_argument(
        "--nights", type=int, default=2, help="Number of nights (default: 2)"
    )
    parser.add_argument(
        "--adults", type=int, default=2, help="Number of adults (default: 2)"
    )
    parser.add_argument(
        "--rooms", type=int, default=1, help="Number of rooms (default: 1)"
    )
    parser.add_argument("--currency", type=str, default="ILS", help="currency")
    parser.add_argument(
        "--max_price", type=float, default=1500, help="Maximum price in ILS"
    )
    parser.add_argument(
        "--loop", action="store_true", help="Run in loop mode (check every 5 minutes)"
    )
    args = parser.parse_args()

    base_url = "https://oporacountryliving.reserve-online.net/"

    params = {
        "checkin": args.checkin,
        "rooms": args.rooms,
        "nights": args.nights,
        "adults": args.adults,
        "currency": args.currency,
    }
    url = f"{base_url}?{urlencode(params)}"

    driver = get_driver()
    logger.info("Starting availability checker for Opora Country Living...")

    try:
        if args.loop:
            while True:

                available_rooms = check_availability(
                    driver,
                    url,
                    checkin=args.checkin,
                    nights=args.nights,
                    adults=args.adults,
                    rooms=args.rooms,
                    max_price=args.max_price,
                )
                if available_rooms:
                    send_email(
                        rooms=available_rooms, max_price=args.max_price
                    )
                time.sleep(300)  # Wait 5 minutes
        else:
            available_rooms = check_availability(
                driver,
                url,
                checkin=args.checkin,
                nights=args.nights,
                adults=args.adults,
                rooms=args.rooms,
                max_price=args.max_price,
            )
            send_email(
                        rooms=available_rooms, max_price=args.max_price
            )
            print(available_rooms)
    except KeyboardInterrupt:
        logger.info("Loop interrupted by user")
    except Exception as e:
        logger.error(f"Error in main loop: {e}")
    finally:
        driver.quit()
        logger.info("WebDriver closed.")


if __name__ == "__main__":
    main()

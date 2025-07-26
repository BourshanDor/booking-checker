# Booking Availability Checker

Python script to automatically check room availability and send email notifications when rooms are available within a specified price range.


## Requirements

- Python 3.8 or higher  
- Google Chrome installed  
- Required Python packages (install with pip):  
  `pip install selenium webdriver-manager tenacity python-dotenv`

---

## Setup

1. Create a `.env` file in your project directory with the following content:

```
EMAIL_USER=your_email@gmail.com
EMAIL_PASSWORD=your_app_password
EMAIL_RECIPIENTS=recipient1@gmail.com,recipient2@gmail.com
```

> **Note:** For Gmail, use an [App Password](https://myaccount.google.com/apppasswords) instead of your regular account password.

2. Customize `email_template.html` if you want to adjust the email appearance (optional).

---

## Usage

Run the script from the command line:


### Available options:

- `--checkin` — Check-in date (format: YYYY-MM-DD). Default: `2025-09-30`  
- `--nights` — Number of nights. Default: `2`  
- `--adults` — Number of adults. Default: `2`  
- `--rooms` — Number of rooms. Default: `1`  
- `--currency` — Currency code. Default: `ILS`  
- `--max_price` — Maximum room price to notify. Default: `1500`  
- `--loop` — Run continuously every 5 minutes (polling mode). Default: Disabled

Example — check availability for 3 nights starting Oct 5, with max price 1200, looping every 5 minutes:
```
python booking.py --checkin 2025-10-05 --nights 3 --max_price 1200 --loop
```




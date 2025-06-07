# Subdomain Finder Bot
Telegram bot to find subdomains for a given domain.

# ðŸ” Subdomain Finder Bot

A powerful Telegram bot for finding subdomains using OSINT tools like `subfinder`. Built for ethical hackers, bug bounty hunters, and cybersecurity researchers.

---

## ðŸš€ Features

- âœ… Finds subdomains for any domain
- âš™ï¸ Uses `subfinder` binary for fast and accurate results
- ðŸ¤– Works via Telegram bot interface
- ðŸ” Lightweight and easy to run

---

## ðŸ“¦ Installation

1. **Clone the repository:**

```bash
git clone https://github.com/itachiuchiha786ii/Subdomain-finder-bot.git
cd Subdomain-finder-bot
```

2. **Install Python dependencies:**

```bash
pip install -r requirements.txt
```

---

## âš™ï¸ Subfinder Setup (Required)

The bot uses [`subfinder`](https://github.com/projectdiscovery/subfinder) to enumerate subdomains.

### Install `subfinder`:

```bash
# On Linux/Termux
wget https://github.com/projectdiscovery/subfinder/releases/latest/download/subfinder-linux-amd64.tar.gz
tar -xvzf subfinder-linux-amd64.tar.gz
chmod +x subfinder
mv subfinder ~/bin/  # or anywhere in your $PATH
```

> âœ… Confirm it's working:
```bash
subfinder -h
```

---

## ðŸ’¡ Usage

Run the bot:

```bash
python bot.py
```

Then in Telegram:

1. Start the bot
2. Send any domain list file 
3. The bot will return discovered subdomains using subfinder

---

## â˜ï¸ Hosting on VPS (Optional but Recommended)

To keep your bot always online, host it on a VPS:

1. Use services like DigitalOcean, AWS, or any Linux VPS
2. Upload your files using `scp` or Git clone on the server
3. Run your bot in the background using:

```bash
nohup python bot.py &
```

4. Or use `screen` or `tmux` to manage sessions.

---

## ðŸ“œ License

This project is licensed under the **MIT License** â€” see the [LICENSE](LICENSE) file for details.

---

## ðŸ¤ Author

Made with â¤ï¸ by [itachiuchiha786ii](https://github.com/itachiuchiha786ii)

import requests
import time
from bs4 import BeautifulSoup
from datetime import datetime
import random
import json

class WalmartStockMonitor:
    def __init__(self, product_url, webhook_url, check_interval=300):
        """
        Initialize the stock monitor
        
        Args:
            product_url (str): Full Walmart product URL
            webhook_url (str): Discord webhook URL
            check_interval (int): Time between checks in seconds (default: 300)
        """
        self.product_url = product_url
        self.webhook_url = webhook_url
        self.check_interval = check_interval
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.5',
            'Connection': 'keep-alive',
        }
        self.last_status = None
        
    def check_stock(self):
        """Check if the product is in stock"""
        try:
            response = requests.get(self.product_url, headers=self.headers)
            response.raise_for_status()
            
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # Check for common out-of-stock indicators
            out_of_stock_indicators = [
                'out of stock',
                'Out of stock',
                'Out Of Stock',
                'Oops! This item is unavailable'
            ]
            
            page_text = soup.get_text().lower()
            is_out_of_stock = any(indicator.lower() in page_text for indicator in out_of_stock_indicators)
            
            # Try to get the product name
            product_name = soup.find('h1')
            product_name = product_name.text if product_name else "Unknown Product"
            
            # Try to get the price
            price_element = soup.find(class_='price-characteristic')
            price = price_element.text if price_element else "Price not found"
            
            return {
                'timestamp': datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                'product_name': product_name,
                'in_stock': not is_out_of_stock,
                'price': price,
                'url': self.product_url
            }
            
        except requests.RequestException as e:
            print(f"Error checking stock: {str(e)}")
            return None

    def send_discord_message(self, status):
        """Send status update to Discord webhook"""
        if status is None:
            return

        # Create Discord embed
        embed = {
            "title": status['product_name'],
            "description": f"Status Update for Walmart Product",
            "url": self.product_url,
            "color": 65280 if status['in_stock'] else 16711680,  # Green if in stock, Red if out of stock
            "fields": [
                {
                    "name": "Status",
                    "value": "🟢 In Stock" if status['in_stock'] else "🔴 Out of Stock",
                    "inline": True
                },
                {
                    "name": "Price",
                    "value": status['price'],
                    "inline": True
                },
                {
                    "name": "Last Checked",
                    "value": status['timestamp'],
                    "inline": True
                }
            ],
            "footer": {
                "text": "Walmart Stock Monitor"
            }
        }

        # Only send message if status has changed or it's been more than an hour
        should_send = (
            self.last_status is None or
            self.last_status['in_stock'] != status['in_stock'] or
            self.last_status['price'] != status['price']
        )

        if should_send:
            webhook_data = {
                "embeds": [embed]
            }

            try:
                response = requests.post(
                    self.webhook_url,
                    json=webhook_data
                )
                response.raise_for_status()
                self.last_status = status
                print(f"Discord message sent at {status['timestamp']}")
            except requests.RequestException as e:
                print(f"Error sending Discord message: {str(e)}")

    def start_monitoring(self):
        """Start the monitoring loop"""
        print(f"Started monitoring {self.product_url}")
        print("Press Ctrl+C to stop monitoring")
        
        while True:
            try:
                status = self.check_stock()
                if status:
                    self.send_discord_message(status)
                
                # Add random delay to avoid detection
                jitter = random.uniform(-30, 30)
                sleep_time = self.check_interval + jitter
                time.sleep(sleep_time)
                
            except KeyboardInterrupt:
                print("\nMonitoring stopped by user")
                break
            except Exception as e:
                print(f"Error in monitoring loop: {str(e)}")
                time.sleep(self.check_interval)

if __name__ == "__main__":
    # Get environment variables
    product_url = os.getenv('WALMART_URL')
    webhook_url = os.getenv('DISCORD_WEBHOOK_URL')
    
    # Validate environment variables
    if not product_url or not webhook_url:
        print("Error: Missing required environment variables.")
        print("Please make sure WALMART_URL and DISCORD_WEBHOOK_URL are set in your .env file")
        exit(1)
    
    # Create monitor instance (check every 5 minutes)
    monitor = WalmartStockMonitor(product_url, webhook_url, check_interval=3600) #used to be 300 for 5 minutes
    
    # Start monitoring
    monitor.start_monitoring()
from WikiSummarizer import summarizer
import time
import slack
from dotenv import load_dotenv
import os
import re
import zmq


class WikiSummarizerBot:

    WELCOME_BLOCK = {
        "type": "section",
        "text": {
            "type": "mrkdwn",
            "text": (
                "Welcome to Slack! :wave: We're so glad you're here. :blush:\n\n*Get started by following the steps below:*"
            ),
        }
    }

    DIVIDER_BLOCK = {"type": "divider"}

    INSTR_BLOCK = {
        "type": "section",
        "text": {
            "type": "mrkdwn",
            "text": '• Type *<https://myslackbottes-7ny4584.slack.com/archives/D011P1PBL64|@WikiSummarizerBot> summarize "<topic>"* to get a short summary of the <topic>\n\n• Type *<https://myslackbottes-7ny4584.slack.com/archives/D011P1PBL64|@WikiSummarizerBot> summarize "<topic>" <num_lines>* to get an <num_lines>-lined summary of the <topic>\n'
        }
    }

    PROCESSING_ERR_BLOCK = {
        "type": "section",
        "text": {
            "type": "mrkdwn",
            "text": 'Uh oh! There was some error processing your request :sweat:. Please try again later...'
        }
    }

    PG_ERR_BLOCK = {
        "type": "section",
        "text": {
            "type": "mrkdwn",
            "text": 'Sorry! Unable to find the requested page'
        }
    }

    def __init__(self, port=8500):
        print("Initializing WikiSummarizer Bot...")
        dotenv_path = os.path.join(os.path.dirname(__file__), '.env')
        load_dotenv(dotenv_path)
        slack_token = os.environ["SLACK_TOKEN"]
        self.client = slack.WebClient(token=slack_token)
        self.bot_id = self.client.auth_test()["user_id"]
        self.events_responded = []

        self.intro_keywords = ["hello", "hi", "yo"]

        self.wiki_summarizer = summarizer.WikiSummarizer()

        context = zmq.Context()
        self.ip = "tcp://0.0.0.0:" + str(port)
        self.zmq_socket = context.socket(zmq.REP)
        self.zmq_socket.bind(self.ip)
        time.sleep(2)

    ##################################################### Utility Functions #########################################################
    def getIntroMsg(self, channel):
        msg_payload = {
            "channel": channel,
            "icon_emoji": ":robot_face:",
            "blocks": [
                self.WELCOME_BLOCK,
                self.DIVIDER_BLOCK,
                self.INSTR_BLOCK
            ]
        }

        return msg_payload

    def getSummaryMsg(self, channel, topic, num_lines=7):
        summary = self.wiki_summarizer.getSummary(topic, num_lines)

        msg_payload = {
            "channel": channel,
            "icon_emoji": ":robot_face:",
            "blocks": [
                {
                    "type": "section",
                    "text": {
                        "type": "mrkdwn",
                        "text": (
                            "*Topic:* " + topic
                        ),
                    }
                },
                self.DIVIDER_BLOCK,
                {
                    "type": "section",
                    "text": {
                        "type": "mrkdwn",
                        "text": (
                            "*Summary:* " + summary
                        ),
                    }
                }
            ]
        }

        return msg_payload



    def getErrorMsg(self, channel):
        msg_payload = {
            "channel": channel,
            "icon_emoji": ":robot_face:",
            "blocks": [
                self.PROCESSING_ERR_BLOCK
            ]
        }

        return msg_payload
    
    def getPageErrorMsg(self, channel):
        msg_payload = {
            "channel": channel,
            "icon_emoji": ":robot_face:",
            "blocks": [
                self.PG_ERR_BLOCK
            ]
        }

        return msg_payload


    def handleEvent(self, event):
        if event["type"] == "app_mention" and event["event_ts"] not in self.events_responded:
            # bot_id = "U011P1PB9NC"
            self.events_responded.append(event["event_ts"])
            msg_payload = {}
            if "%s" % self.bot_id in event["text"]:
                try:
                    print("\n\nMsg directed for Bot\n\n")
                    if event["text"].split()[1] == "summarize":
                        print("\n\nSummarize\n\n")
                        search = re.search('\"(.*?)\"', event["text"])
                        topic = search.group(1)
                        if search.end() == len(event["text"]):
                            msg_payload = self.getSummaryMsg(event["channel"], topic)
                        else:
                            num_lines = int(event["text"][search.end()+1:])
                            msg_payload = self.getSummaryMsg(event["channel"], topic, num_lines)
                    
                    elif any(word in event["text"].lower() for word in self.intro_keywords):
                        print("\n\nIntro\n\n")
                        msg_payload = self.getIntroMsg(event["channel"])

                    else:
                        print("\n\nError\n\n")
                        msg_payload = self.getErrorMsg(event["channel"])
                    
                    response = self.client.chat_postMessage(**msg_payload)
                
                except Exception as e:
                    print("\n\nPg not found\n\n")
                    msg_payload = self.getPageErrorMsg(event["channel"])
                    response = self.client.chat_postMessage(**msg_payload)
        return {}
            
    def start(self):
        print("WikiSummarizer Bot started on", self.ip)
        print("Press Ctrl+C to stop the service...")

        try:
            while True:
                data = self.zmq_socket.recv_json()
                # print("Received request: ", data)
                resp = self.handleEvent(data)
                self.zmq_socket.send_json(resp)
        except KeyboardInterrupt:
            print("\rWikiSummarizer Bot stopped.")
        except Exception as e:
            print(e)
        finally:
            exit(0)

if __name__ == '__main__':
    slackbot = WikiSummarizerBot()
    slackbot.start()
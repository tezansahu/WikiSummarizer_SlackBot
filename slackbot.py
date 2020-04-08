from WikiSummarizer import summarizer
import time
import slack
from dotenv import load_dotenv
import os
import re
import zmq
from concurrent.futures import ThreadPoolExecutor



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
            "text": '• Type *<https://myslackbottes-7ny4584.slack.com/archives/D011P1PBL64|@WikiSummarizerBot> summarize "<topic>"* to get a short summary of the <topic>\n\n' +
            '• Type *<https://myslackbottes-7ny4584.slack.com/archives/D011P1PBL64|@WikiSummarizerBot> summarize "<topic>" <num_lines>* to get a <num_lines>-lined summary of the <topic>\n\n' +
            '• Type *<https://myslackbottes-7ny4584.slack.com/archives/D011P1PBL64|@WikiSummarizerBot> summarize "<topic-1>" "<topic-2>" ...* to get a summary of each of the topics <topic-1>, <topic-2>, etc.\n\n' +
            '• Type *<https://myslackbottes-7ny4584.slack.com/archives/D011P1PBL64|@WikiSummarizerBot> summarize "<topic-1>" "<topic-2>" ... <num-lines>* to get a <num_lines>-lined summary of each of the topics <topic-1>, <topic-2>, etc.\n\n'
        }
    }

    ERR_BLOCK = {
        "type": "section",
        "text": {
            "type": "mrkdwn",
            "text": ''
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
                self.INSTR_BLOCK,
                self.DIVIDER_BLOCK
            ]
        }

        return msg_payload

    def getSummaryMsg(self, channel, topic, num_lines=7):
        summary = self.wiki_summarizer.getSummary(topic, num_lines)

        if summary == "PageError":
            return self.getErrorMsg(channel, "PageNotFoundError", topic)

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
                },
                self.DIVIDER_BLOCK
            ]
        }

        return msg_payload


    def getErrorMsg(self, channel, err_type, topic=None):
        msg_payload = {
            "channel": channel,
            "icon_emoji": ":robot_face:",
            "blocks": [
                self.ERR_BLOCK,
                self.DIVIDER_BLOCK
            ]
        }

        if err_type == "ProcessingError":
            msg_payload["blocks"][0]["text"]["text"] = "Uh oh! There was some error processing your request :sweat:. Please try again later..."
        elif err_type == "PageNotFoundError":
            msg_payload["blocks"][0]["text"]["text"] = "Sorry! Unable to find the requested page: " + topic
        elif err_type == "InvalidRequestError":
            msg_payload["blocks"][0]["text"]["text"] = "Umm...I do not understand how to handle this request :sweat:. Currently I am only trained to summarize topics. Please follow the syntax for doing so: "
            msg_payload["blocks"] = msg_payload["blocks"] + [self.DIVIDER_BLOCK, self.INSTR_BLOCK]

        return msg_payload


    def sendSummary(self, data):
        try:
            print(data["channel"], data["topic"], data["num_lines"])
            msg_payload = self.getSummaryMsg(data["channel"], data["topic"], data["num_lines"])
            response = self.client.chat_postMessage(**msg_payload)
        except Exception as e:
            msg_payload = self.getErrorMsg(event["channel"], "ProcessingError")
            response = self.client.chat_postMessage(**msg_payload)

    
    def handleEvent(self, event):
        if event["type"] == "app_mention" and event["event_ts"] not in self.events_responded:
            self.events_responded.append(event["event_ts"])
            msg_payload = {}
            if "%s" % self.bot_id in event["text"]:
                try:
                    if event["text"].split()[1] == "summarize":
                        
                        topics = re.findall('\"(.*?)\"', event["text"])
                        unique_topics = set(topics)
                        num_lines = 7 if event["text"].rfind(topics[-1]) + len(topics[-1]) + 1 == len(event["text"]) else int(event["text"][event["text"].rfind(topics[-1]) + len(topics[-1]) + 1:])

                        with ThreadPoolExecutor(max_workers = len(unique_topics)) as executor:
                            for topic in unique_topics:
                                print("Starting ", topic)
                                future = executor.submit(self.sendSummary, ({"channel": event["channel"], "topic": topic, "num_lines": num_lines}))

                    elif event["text"].lower().split()[0] in self.intro_keywords:
                        msg_payload = self.getIntroMsg(event["channel"])
                        response = self.client.chat_postMessage(**msg_payload)

                    else:
                        msg_payload = self.getErrorMsg(event["channel"], "InvalidRequestError")
                        response = self.client.chat_postMessage(**msg_payload)
                    
                except Exception as e:
                    msg_payload = self.getErrorMsg(event["channel"], "ProcessingError")
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
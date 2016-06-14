import requests
import json
# import matplotlib.pyplot as plt
import boto3
import time
from botocore.handlers import disable_signing


BASE_URL = 'http://dev.markitondemand.com/MODApis/Api/v2/InteractiveChart'
# QUEUE_URL = 'https://sqs.us-west-2.amazonaws.com/557989321320/stock-compare-queue'
QUEUE_URL = 'https://sqs.us-west-1.amazonaws.com/497100832806/stock-compare-queue'
# RESULT_URL = 'http://192.168.1.103:2000/compare'
# RESULT_URL = 'http://stock-data-component.us-west-2.elasticbeanstalk.com/compare'
RESULT_URL = 'stock-data.us-west-1.elasticbeanstalk.com/compare'


class MatchServer(object):
    def getData(self, stock_name, days):
        payload = {
            "Normalized": False,
            "NumberOfDays": days,
            "DataPeriod": "Day",
            "Elements": [{
                "Symbol": stock_name,
                "Type": "price",
                "Params": ["c"]
            }]
        }
        request = requests.get(BASE_URL + '/json?parameters=' + json.dumps(payload, ensure_ascii=True))
        print request.status_code
        response_data = json.loads(request.text)
        return response_data

    def compareStock(self, stock_a, days_a, stock_b, days_b):
        data_a = self.getData(stock_a, days_a)
        data_b = self.getData(stock_b, days_b)
        vals_a = data_a['Elements'][0]['DataSeries']['close']['values']
        vals_b = data_b['Elements'][0]['DataSeries']['close']['values']
        if stock_b == stock_a:
            vals_b[-len(vals_a):] = []
        match_range = self.matchCurve(vals_a, vals_b)
        print match_range
        data_b['Dates'] = data_b['Dates'][match_range[0]:match_range[1]]
        data_b['Positions'] = data_b['Positions'][match_range[0]:match_range[1]]
        data_b['Elements'][0]['DataSeries']['close']['values'] = \
            data_b['Elements'][0]['DataSeries']['close']['values'][match_range[0]:match_range[1]]
        result = {
                    'stockA': data_a,
                    'stockB': data_b
                  }
        # vals_b = data_b['Elements'][0]['DataSeries']['close']['values']
        # plt.plot(range(len(vals_a)), vals_a, 'r', range(len(vals_b)), vals_b, 'b')
        # plt.show()
        return result

    def matchCurve(self, arrA, arrB):
        # B should be longer than A
        min_dev = float('Inf')
        min_head = 0
        for i in xrange(len(arrB)-len(arrA)+1):
            nmA = self.normalize(arrA)
            nmB = self.normalize(arrB[i:i+len(arrA)])
            dev = self.calDev(nmA, nmB)
            if dev < min_dev:
                min_head = i
                min_dev = dev
        return [min_head, min_head+len(arrA)]

    def calDev(self, arrA, arrB):
        acc_dev = 0
        for i in xrange(len(arrA)):
            acc_dev += (arrA[i] - arrB[i]) ** 2
        return acc_dev

    def normalize(self, arr):
        mx = max(arr)
        mn = min(arr)
        return [(elem - mn)/(mx - mn) for elem in arr]

    def getRequestFromQueue(self, Q):
        msgs = Q.receive_messages()
        if len(msgs) == 0:
            print 'No request'
        else:
            msg = msgs[0]
            print msg.body
            data = json.loads(msg.body)
            stkA, stkB, days, id = data['stockA'], data['stockB'], data['days'], data['id']
            print stkA, stkB, days, id
            rst = self.compareStock(stkA, days, stkB, 5000)
            rst['id'] = id
            r = requests.post(RESULT_URL, json=rst)
            msg.delete()
            print r.status_code

    def mainLoop(self):
        sqs = boto3.resource('sqs', region_name='us-west-1')
        sqs.meta.client.meta.events.register('choose-signer.sqs.*', disable_signing)
        q = sqs.Queue(url=QUEUE_URL)
        while True:
            self.getRequestFromQueue(q)
            time.sleep(1)


if __name__ == "__main__":
    S = MatchServer()
    S.mainLoop()


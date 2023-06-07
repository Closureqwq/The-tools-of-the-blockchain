import backtrader as bt
import pandas as pd
import yfinance as yf

class RSI(bt.Indicator):
    lines = ('rsi',)
    params = (('period',4),)

    def __init__(self):
        self.addminperiod(self.params.period)

    def next(self):
        if len(self.data) >= self.params.period:
            gains = [self.data.close[i] - self.data.close[i - 1] if self.data.close[i] > self.data.close[i - 1] else 0
                 for i in range(-self.params.period, 0)]
            losses = [self.data.close[i - 1] - self.data.close[i] if self.data.close[i] < self.data.close[i - 1] else 0
                  for i in range(-self.params.period, 0)]
            average_gain = sum(gains) / self.params.period
            average_loss = sum(losses) / self.params.period
            rs = average_gain / average_loss if average_loss != 0 else float('inf')  
            self.lines.rsi[0] = 100 - (100 / (1 + rs))


class LongShortRatio(bt.Indicator):
    lines = ('lsr',)
    params = (('period',4),)

    def __init__(self):
        self.addminperiod(self.params.period)

    def next(self):
        weighted_longs = sum([(self.data.close[i] - self.data.open[i]) / self.data.open[i] * self.data.volume[i] 
                              if self.data.close[i] > self.data.open[i] else 0
                              for i in range(-self.params.period, 0)])
        weighted_shorts = sum([(self.data.open[i] - self.data.close[i]) / self.data.open[i] * self.data.volume[i] 
                               if self.data.close[i] < self.data.open[i] else 0
                               for i in range(-self.params.period, 0)])
        self.lines.lsr[0] = weighted_longs / weighted_shorts if weighted_shorts != 0 else 1


class RsiStrategy(bt.Strategy):
    params = (
        ('rsi_oversold',),  
        ('rsi_overbought',),  
        ('lsr_high',), 
        ('lsr_low', ),  
        ('stop_loss',),
        ('take_profit',),
    )

    def __init__(self):
        self.rsi = RSI(self.data)
        self.lsr = LongShortRatio(self.data)
        self.order = None

    def log(self, txt, dt=None):
        dt = dt or self.datas[0].datetime.date(0)
        print('%s, %s' % (dt.isoformat(), txt))

    def calculate_size(self):
        return 0.8 * self.broker.getcash() / self.data.close[0]

    def notify_order(self, order):
        if order.status in [order.Submitted, order.Accepted]:
            return
        if order.status in [order.Completed]:
            if order.isbuy():
                self.log('BUY EXECUTED, %.2f' % order.executed.price)
            elif order.issell():
                self.log('SELL EXECUTED, %.2f' % order.executed.price)
        elif order.status in [order.Canceled, order.Margin, order.Rejected]:
            self.log('Order Canceled/Margin/Rejected')
            self.order = None 

    def next(self):
        if not self.position:
            if self.rsi < self.params.rsi_oversold and self.lsr > self.params.lsr_high:
                self.buy(size=self.calculate_size())
        else:
            if self.data.close[0] >= self.position.price * (1 + self.params.take_profit):
                self.sell(size=self.position.size)
            elif self.data.close[0] <= self.position.price * (1 - self.params.stop_loss):
                self.sell(size=self.position.size)

cerebro = bt.Cerebro()
cerebro.addstrategy(RsiStrategy)

data = yf.download('BTC-USD', start='', end='')
datafeed = bt.feeds.PandasData(dataname=data)
cerebro.adddata(datafeed)

cerebro.broker.setcash()
cerebro.broker.set_coc(True) 

print('Starting Portfolio Value: %.2f' % cerebro.broker.getvalue())

cerebro.addanalyzer(bt.analyzers.AnnualReturn, _name='annual_return')
cerebro.addanalyzer(bt.analyzers.TimeReturn, _name='monthly_return', timeframe=bt.TimeFrame.Months)
cerebro.addanalyzer(bt.analyzers.SharpeRatio, _name='sharpe_ratio')
cerebro.addanalyzer(bt.analyzers.DrawDown, _name='drawdown')
cerebro.addanalyzer(bt.analyzers.Transactions, _name='transactions')
cerebro.addanalyzer(bt.analyzers.TradeAnalyzer, _name='tradeanalyzer')

results = cerebro.run()

print('Final Portfolio Value: %.2f' % cerebro.broker.getvalue())

annual_return = results[0].analyzers.getbyname('annual_return').get_analysis()
monthly_return = results[0].analyzers.getbyname('monthly_return').get_analysis()
sharpe_ratio = results[0].analyzers.getbyname('sharpe_ratio').get_analysis()
drawdown = results[0].analyzers.getbyname('drawdown').get_analysis()
transactions = results[0].analyzers.getbyname('transactions').get_analysis()
tradeanalyzer = results[0].analyzers.getbyname('tradeanalyzer').get_analysis()

print('Annual Average Return: %.2f%%' % ((sum(annual_return.values()) / len(annual_return)) * 100))
print('Monthly Average Return: %.2f%%' % ((sum(monthly_return.values()) / len(monthly_return)) * 100))
print('Sharpe Ratio:', sharpe_ratio)
print('Max Drawdown:', drawdown['max']['drawdown'])

for date, trans_list in transactions.items():
    for transaction in trans_list:
        print('Transaction on %s: %s %s at price %.2f' % (date, transaction[0], transaction[1], transaction[2]))

print('Total transactions:', len(transactions))


print('TradeAnalyzer:')
for key, value in tradeanalyzer.items():
    print(f'{key}: {value}')

cerebro.plot(style='candlestick')

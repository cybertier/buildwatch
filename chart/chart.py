import matplotlib.pyplot as plt
import numpy as np

labels = ['t0', 't-1', 't-2']
labels.reverse()
rpc = [0, 0, 1]
opencv = [0, 1242, 4]
eslint_config = [4, 1, 8]
eslint_scope = [0, 0, 6]
kraken_api = [5, 0, 13]
mariadb = [272, 2, 72]

x = np.arange(len(labels))  # the lab
# el locations
width = 0.15  # the width of the bars

fig, ax = plt.subplots()
rects1 = ax.bar(x - (width * 2.5), rpc, width, label='RPC-Websocket')
rects2 = ax.bar(x - width*1.5, opencv, width, label='Opencv.js')
rects3 = ax.bar(x - width/2, eslint_config, width, label='Eslint-Config')
rects4 = ax.bar(x + (width * 0.5), kraken_api, width, label='Kraken Api')
rects5 = ax.bar(x + (width*1.5), mariadb, width, label='Maria DB')
rects6 = ax.bar(x + width*2.5, eslint_scope, width, label='Eslint-Scope')

# Add some text for labels, title and custom x-axis tick labels, etc.
ax.set_ylabel('Newly introduced artefacts observed by Buildwatch')
ax.set_title('Artefacts of different packages and versions')
ax.set_xticks(x)
ax.set_yscale('log')
ax.set_yticks([ 1, 10, 100, 1000, 10000])
ax.set_xticklabels(labels)
ax.legend()


def autolabel(rects):
    """Attach a text label above each bar in *rects*, displaying its height."""
    for rect in rects:
        height = rect.get_height()
        ax.annotate('{}'.format(height),
                    xy=(rect.get_x() + rect.get_width() / 2, height if height else 1),
                    xytext=(0, 3),  # 3 points vertical offset
                    textcoords="offset points",
                    color= rects.patches[0].get_facecolor(),
                    ha='center', va='bottom')


autolabel(rects1)
autolabel(rects2)
autolabel(rects3)
autolabel(rects4)
autolabel(rects5)
autolabel(rects6)

fig.tight_layout()

plt.show()

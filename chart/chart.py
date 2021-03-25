import matplotlib.pyplot as plt
import numpy as np

labels = ['t0', 't-1', 't-2']
labels.reverse()
men_means = [0, 0, 1]
women_means = [0, 2730, 4]

x = np.arange(len(labels))  # the lab
# el locations
width = 0.35  # the width of the bars

fig, ax = plt.subplots()
rects1 = ax.bar(x - width / 2, men_means, width, label='RPC-Websocket')
rects2 = ax.bar(x + width / 2, women_means, width, label='Opencv.js')

# Add some text for labels, title and custom x-axis tick labels, etc.
ax.set_ylabel('Newly introduced artefacts observed by Buildwatch')
ax.set_title('Artefacts of different packages and versions')
ax.set_xticks(x)
ax.set_yscale('log')
ax.set_yticks([1, 10, 100, 1000, 10000])
ax.set_xticklabels(labels)
ax.legend()


def autolabel(rects):
    """Attach a text label above each bar in *rects*, displaying its height."""
    for rect in rects:
        height = rect.get_height()
        ax.annotate('{}'.format(height),
                    xy=(rect.get_x() + rect.get_width() / 2, height),
                    xytext=(0, 3),  # 3 points vertical offset
                    textcoords="offset points",
                    ha='center', va='bottom')


autolabel(rects1)
autolabel(rects2)

fig.tight_layout()

plt.show()

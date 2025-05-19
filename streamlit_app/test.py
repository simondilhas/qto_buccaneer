import pandas as pd
import plotly.express as px

# raw data
data = [
    ['HNF Total', 1664.2578, 'm2', True, 0.0019, '02_flugge'],
    ['NNF Total', 465.4945, 'm2', True, 0.0038, '02_flugge'],
    ['HNF Total', 1702.7585, 'm2', True, 0.0014, '03_symmetrie'],
    ['NNF Total', 531.0565, 'm2', True, 0.0028, '03_symmetrie'],
    ['HNF Total', 1648.9436, 'm2', True, 0.0014, '05_schole'],
    ['NNF Total', 472.2768, 'm2', True, 0.0028, '05_schole'],
    ['HNF Total', 1647.2758, 'm2', True, 0.0018, '08_the-conversation'],
    ['NNF Total', 485.7661, 'm2', True, 0.0038, '08_the-conversation'],
]

# create DataFrame
df = pd.DataFrame(data, columns=['metric_name', 'value', 'Unit', 'Valid', 'Ratio', 'building'])

# plot
fig = px.bar(df, x='building', y='value', color='metric_name', barmode='group',
             labels={'value': 'Area (m²)', 'building': 'Building', 'metric_name': 'Metric'},
             title='HNF and NNF per Project')

fig.update_layout(xaxis_title='Building', yaxis_title='Area (m²)', title_x=0.5)

fig.show()

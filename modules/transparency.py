import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
import ipywidgets
import re
from plotly.offline import download_plotlyjs, init_notebook_mode, plot, iplot, iplot_mpl

init_notebook_mode(connected=True)
plt.rcParams['savefig.dpi'] = 150

def get_data():
    text_to_number = lambda t: sum(int(number) for number in re.findall('(\d+)€', t.replace('.', '').replace(' ', ''))) if isinstance(t, str) else 0.0

    df = pd.read_csv('../data/corruption_propre.csv').drop('Unnamed: 0', axis=1)
    df['date des faits'] = pd.to_datetime(df['date des faits'])
    df['date de la condamnation'] = pd.to_datetime(df['date de la condamnation'])
    df['duree'] = (df['date de la condamnation'] - df['date des faits']).dt.days / 365.25
    df['amende_numerique'] = df['Amendes'].apply(text_to_number)

    def montant_scaler(series):
        mini = min(series)
        maxi = pd.np.percentile(series, 90)# max(series)
        return 10 + pd.np.minimum(30, (pd.np.sqrt((series-mini)/(maxi-mini))*10)).fillna(value=0)
    df['size_amande'] = montant_scaler(df['amende_numerique'].fillna(value=0))
    df['size_amande'] = montant_scaler(df['Montants numérique du préjudice'].fillna(value=0))
    # df['size_prejudice'] = df['Montants numérique du préjudice'].apply(montant_scaler)
    for col, types in zip(df.dtypes.index, df.dtypes):
        if types == 'object':
            df[col].fillna(value='na', inplace=True)
        else:
            df[col].fillna(value=0.0, inplace=True)
    print('Data Loaded.')
    return df

def create_all_data(df, cibles_categories):
    all_data = pd.DataFrame()
    for i, cible in enumerate(cibles_categories):
        data = pd.DataFrame([
                (id_, tag) for (tags, id_) in zip(df[cible], df['id'])
                if isinstance(tags, str)
                for tag in tags.split(';')
            ], columns=['id', cible])
        if i == 0:
            all_data = data
        else:
            # print(cible)
            all_data = all_data.merge(data, on="id")
    return all_data

cibles_categories = [
     'juridiction du jugement',
     'vie publique',
     'département',
     'région',
     'tags',
     'entités impliquées',
     'infractions pertinentes',
     # 'duree'
    ]
df = get_data()
all_data = create_all_data(df, cibles_categories)


def create_histo_duree(cible):
    data = pd.DataFrame([
            (tag, duree) for (tags, duree) in zip(df[cible], df['duree'])
            if isinstance(tags, str)
            for tag in tags.split(';')
        ], columns=[cible, 'duree'])
    top_cible = data[cible].value_counts()
    top_cible = top_cible[0: min(20, len(top_cible))].index
    top_cible = list(reversed(top_cible))
    data = data.loc[data[cible].isin(top_cible)]
    sorted_cible = data.groupby(cible)['duree'].mean().sort_values().index
    plt.figure(figsize=(10, len(top_cible)*0.4), dpi=200)
    sns.barplot(data=data, x='duree', y=cible, order=sorted_cible, palette='Reds')
    # sns.boxplot(data=data, x='duree', y=cible, order=sorted_cible, palette='Reds')
    plt.xlabel('Années avant condamnation vs <{:s}>'.format(cible))
    plt.ylabel('')

def make_interactive_duree():
    ipywidgets.interact(create_histo_duree, cible=cibles_categories)

def create_histo_nombre(cible):
    data = pd.Series([ tag for tags in df[cible] if isinstance(tags, str)  for tag in tags.split(';')])
    data = data.value_counts() # [].sort_values()
    data = data[0: min(20, len(data))].sort_values()
    plt.figure(figsize=(10, len(data)*0.4), dpi=200)
    sns.barplot(x=data, y=data.index, palette='Reds', orient='h')
    plt.xlabel("Nombre d'affaires par <{:s}>".format(cible))

def make_interactive_nombre():
    ipywidgets.interact(create_histo_nombre, cible=cibles_categories)

def create_heatmap(champ1, champ2):
    # On trie les catégories
    cibles = (champ1, champ2)
    cibles0 = all_data[cibles[0]].value_counts()
    cibles0 = cibles0[0: min(20, len(cibles0))].index
    cibles1 = all_data[cibles[1]].value_counts()
    cibles1 = cibles1[0: min(20, len(cibles1))].index

    d = all_data.loc[(all_data[cibles[0]].isin(cibles0)) & (all_data[cibles[1]].isin(cibles1))]

    d = d.dropna(subset=cibles).groupby(cibles).size()
    plt.figure(figsize=(10, 10))
    sns.heatmap(d.unstack(), square=True, linewidths=.5)

def make_interactive_heatmap():
    ipywidgets.interact(create_heatmap, champ1=cibles_categories, champ2=cibles_categories[1:] + [cibles_categories[0]])


def create_scatter_amande():
    # total = df
    text_format = '<br>'.join([
            '<b>Juridiction:</b> {juridiction du jugement:s}',
            '<b>Département:</b> {département:s}',
            '<b>Montant Préjudice:</b> {Montants numérique du préjudice:,.0f} €',
            '<b>Montant Amande:</b> {amende_numerique:,.0f} €'
        ])
    
    data = []
    split = "vie publique"
    for value in df[split].unique():

        total = df.loc[df[split]==value]
        texts = [text_format.format(**row) for _, row in total.iterrows()]
        trace = {
            'x': total['duree'],
            'y': total['juridiction du jugement'],
            'mode': 'markers',
            'marker': {
                'size': total['size_amande']
            },
            'text': texts,
            'hoverinfo': 'text',
            'name': split + ': ' + value
        }
        data.append(trace)
        
    
    layout = {
        'autosize': False,
        'height': 700,
        'width': 900,
        'margin':{
            't': 20,
            'b': 20,
            'l': 300,
            'r': 10
        },
        'hovermode': 'closest'
    }

    iplot({'data':data, 'layout':layout})

def create_histo_montant(cible):
    a_moyenner = "Montants numérique du préjudice"
    data = pd.DataFrame([
            (tag, duree) for (tags, duree) in zip(df[cible], df[a_moyenner])
            if isinstance(tags, str)
            for tag in tags.split(';')
        ], columns=[cible, a_moyenner])
    data = data.loc[data[a_moyenner] > 0]
    top_cible = data[cible].value_counts()
    top_cible = top_cible[0: min(20, len(top_cible))].index
    top_cible = list(reversed(top_cible))
    data = data.loc[data[cible].isin(top_cible)]
    sorted_cible = data.groupby(cible)[a_moyenner].mean().sort_values().index
    plt.figure(figsize=(10, len(top_cible)*0.4), dpi=200)
    # ax  = sns.barplot(data=data, x=a_moyenner, y=cible, order=sorted_cible, palette='Reds')
    ax  = sns.boxplot(data=data, x=a_moyenner, y=cible, order=sorted_cible, palette='Reds')
    plt.xlabel('Montant du préjudice (€) vs <{:s}>'.format(cible))
    plt.ylabel('')
    ax.set_xscale('log')
    plt.xlim([1e3, 1e10])

def make_interactive_montant():
    ipywidgets.interact(create_histo_montant, cible=cibles_categories)



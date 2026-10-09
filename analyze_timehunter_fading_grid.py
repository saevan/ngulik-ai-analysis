"""Exploratory shortlist restricted to current-bar-open fading configurations.

Uses the SAME predefined grid and train/validation ranking restricted to dip
not None. Both shortlists are predefined for the corrected rerun. Earlier
experiments already viewed test data: this is not independent confirmation.
Test results never select or replace this candidate.
"""
import json
import numpy as np
import pandas as pd
from grid_search_timehunter import (OUT, FADING_REFERENCE, SHORTLIST, load_data, prepare, evaluate,
                                   config_of, rank, STOCK_COST, FOREX_COST)


def main():
    train=pd.read_csv(OUT/'train_grid.csv')
    short=rank(train[(train.dip.notna())&(train.train_n>=200)&(train.train_tickers>=20)],'train_').head(SHORTLIST)
    stocks,_=load_data('stocks')
    groups=prepare(stocks)
    rows=[]
    for _, row in short.iterrows():
        s,_=evaluate(groups,config_of(row),start='2015-01-01',stop='2020-01-01')
        item=row.to_dict()
        item.update({'validation_'+k:v for k,v in s.items() if k!='gross'})
        rows.append(item)
    validation=pd.DataFrame(rows)
    validation.to_csv(OUT/'fading_validation_shortlist.csv',index=False)
    selected=rank(validation[(validation.validation_n>=100)&(validation.validation_tickers>=20)],'validation_').iloc[0]
    config=config_of(selected)
    (OUT/'fading_locked_candidate.json').write_text(json.dumps(config,indent=2),encoding='utf-8')
    result={'locked_config':config,'fading_reference':FADING_REFERENCE,
            'result_basis':'gross','cost_model':'none',
            'stock_cost_per_side':STOCK_COST,'forex_cost_per_side':FOREX_COST,
            'shortlist_predefined_for_corrected_run':True,'test_previously_explored':True,
            'train_net_5of5':int(((train.dip.notna())&(train.train_numeric_passes==5)).sum()),
            'validation_net_5of5':int((validation.validation_numeric_passes==5).sum())}
    for label,start,stop in [('train',None,'2015-01-01'),('validation','2015-01-01','2020-01-01'),
                             ('test','2020-01-01',None),('all',None,None)]:
        s,records=evaluate(groups,config,start=start,stop=stop,detail=True)
        trades=pd.DataFrame(records)
        trades['net_return']=(1+trades.gross_return)*(1-STOCK_COST)/(1+STOCK_COST)-1
        trades.to_csv(OUT/f'fading_{label}_trades.csv',index=False)
        s['worst_adverse_excursion']=float(trades.adverse_excursion.min())
        s['unfilled_end_marks']=int((trades.reason=='period_end_mark').sum())
        s['mean_bars']=float(trades.bars.mean())
        s['fading_fraction']=float((trades.reason=='fading').mean())
        result[label]=s
        print(label+': '+json.dumps(s),flush=True)
    forex,_=load_data('forex')
    fx=prepare(forex,dips=[config['dip']])
    result['forex_transfer'],rec=evaluate(fx,config,cost=FOREX_COST,detail=True)
    pd.DataFrame(rec).to_csv(OUT/'fading_forex_trades.csv',index=False)
    (OUT/'fading_summary.json').write_text(json.dumps(result,indent=2),encoding='utf-8')
    print('LOCKED: '+json.dumps(config),flush=True)
    print('VALIDATION PASS COUNT: '+str(result['validation_net_5of5']),flush=True)
    print('FOREX: '+json.dumps(result['forex_transfer']),flush=True)


if __name__=='__main__':
    main()

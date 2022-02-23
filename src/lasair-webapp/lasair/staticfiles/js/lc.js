function plotlc(data){
gmag = []
gfmag = []
ngmag = []
gt = []
gft = []
ngt = []
gerror = []
gferror = []

gra = []
gdec = []

rmag = []
rfmag = []
nrmag = []
rt = []
rft = []
nrt = []
rerror = []
rferror = []

rra = []
rdec = [] 
g = 'rgb(104,139,46)';
r = 'rgb(244,2,52)'; 
ng = 'rgb(216,237,207)';
nr = 'rgb(255,209,209)'; 
candidates = data.candidates;
//first_item = data[0];
//first_ra = Number(first_item.ra)*3600;
//first_dec = Number(first_item.dec)*3600;
first_ra = Number(data.objectData.ramean)*3600;
first_dec = Number(data.objectData.decmean)*3600;
now_mjd = data.objectData.now_mjd;
mjdmin_ago = data.objectData.mjdmin_ago;
mjdmax_ago = data.objectData.mjdmax_ago;
minmag = 100;
maxmag = 0;

candidates.forEach(function(item){
    y = Number(item.magpsf);
    if(y > maxmag){maxmag = y;}
    if(y < minmag){minmag = y;}
    x = Number(item.since_now);
    e = Number(item.sigmapsf);
    x2 = first_ra - Number(item.ra)*3600;
    y2 = first_dec - Number (item.dec)*3600;
    fid = Number(item.fid);
    det = (item.candid)
    if(det){
	pos = (item.isdiffpos == 't' || item.isdiffpos == '1');
        if(fid == 1 && pos){
            gmag.push(y);
            gt.push(x);
            gerror.push(e);
            gra.push(x2);
            gdec.push(y2);
        }
        else if(fid ==2 && pos){
            rmag.push(y);
            rt.push(x);
            rerror.push(e);
            rra.push(x2);
            rdec.push(y2);
        }
        if(fid == 1 && !pos){
            gfmag.push(y);
            gft.push(x);
            gferror.push(e);
            gra.push(x2);
            gdec.push(y2);
        }
        else if(fid ==2 && !pos){
            rfmag.push(y);
            rft.push(x);
            rferror.push(e);
            rra.push(x2);
            rdec.push(y2);
        }
    } else {
        if(fid == 1){
            ngmag.push(y);
            ngt.push(x);
        }
        else if(fid ==2){
            nrmag.push(y);
            nrt.push(x);
        }
    }
});

lc_div = document.getElementById('lc');
var lcg = {x:gt, y: gmag, error_y:{
        type:'data',
        color: g,
        opacity: 0.7,
        array: gerror,
        visible: true
        },
    mode:'markers',
    marker: { color:g, size: 12 },
    type:'scatter'
}
var lcr = {x:rt, y: rmag, error_y:{
        type:'data',
        color: r,
        array: rerror,
        opacity: 0.7,
        visible: true
        },
        mode:'markers',
    marker: { color:r, size: 12 },
        type:'scatter'
}
var lcfg = {x:gft, y: gfmag, error_y:{
        type:'data',
        color: g,
        opacity: 0.7,
        array: gferror,
        visible: true
        },
    mode:'markers',
    marker: { color:g, size: 12, symbol: "circle-open" },
    type:'scatter'
}
var lcfr = {x:rft, y: rfmag, error_y:{
        type:'data',
        color: r,
        array: rferror,
        opacity: 0.7,
        visible: true
        },
        mode:'markers',
    marker: { color:r, size: 12, symbol: "circle-open" },
        type:'scatter'
}
var nlcg = {x:ngt, y: ngmag,
    mode:'markers',
    marker: { color:ng, symbol:"diamond" },
    type:'scatter'
}
var nlcr = {x:nrt, y: nrmag,
    mode:'markers',
    marker: { color:nr, symbol:"diamond" },
    type:'scatter'
}

Plotly.plot(lc_div, [lcg, lcr, lcfg, lcfr, nlcg, nlcr], {
    margin: { t: 0 }, 
    displayModeBar: false, 
    showlegend: false,
    xaxis: {
        title:'MJD - ' + now_mjd,
	rangemode: 'tozero',
        tickformat :".f" },
    yaxis: {
        title: 'Difference Magnitude',
        autorange: 'reversed'    
    },
    shapes: [
        { type:'line', x0:-mjdmin_ago, x1:-mjdmin_ago, y0:minmag, y1:maxmag,
	line: { color: 'blue', dash:'dot'} },
        { type:'line', x0:-mjdmax_ago, x1:-mjdmax_ago, y0:minmag, y1:maxmag,
	line: { color: 'blue', dash:'dot'} },
    ]
  },
    {displayModeBar: false});

radec_div = document.getElementById('radec');

var radecg = {x:gra, y: gdec,
    mode:'markers',
    marker: { color:'rgb(104,139,46)' },
    type:'scatter'
}

var radecr = {x:rra, y: rdec,
    mode:'markers',
    marker: { color:'rgb(244,2,52)' },
    type:'scatter'
}

Plotly.plot(radec_div, [radecg, radecr], {
    margin: { t: 0 },
    showlegend: false,
        width: 370,
        height: 285,
    shapes: [
        {
            type: 'circle',
            xref: '0',
            yref: '0',
            x0: -1.5,
            y0: -1.5,
            x1: 1.5,
            y1: 1.5,
            opacity: 0.3,
            fillcolor: '#bbded6',
            line: {
                color: 'black'
            }
        }]
}, {displayModeBar: false}
);

}


var NROIS = 0;            // number of ROIS -- sufficient for code but not for html
var fits;
var fits_url;
// handy
function gebi (id) {
    return document.getElementById (id);
}

function start_fitsview(_fits, _fits_url) {
    fits = _fits;
    fits_url = _fits_url;
    console.log(fits_url);

// set initial stretch
    var stretch_sel = gebi("stretch_sel");
    if (stretch_sel){
	    console.log(stretch_sel.value);
        fits.setStretch (stretch_sel.value);
    } else {
	    console.log('no stretch div');
        fits.setStretch ("linear");
    }

// add handler to report new ROI
    fits.addROIChangedHandler (onROIChange);

// connect clean up function
    window.onunload = function() {
        if (fits.header_win)
        fits.header_win.close();
    };

// suck up the pixels RDW
    fits.imageFromUrl(fits_url);

}

// called to display header
function showHeader () {
    fits.showHeader(true);
}

// called when a contrast slider is moved
function newContrast (event) {
// collect both values
    var name = event.target.id;
    var number = event.target.id.substring (name.length-1, name.length);
    var contrast_value = gebi ('contrast_slider_' + number).value;

// update tracking number
    var contrast_value_id = gebi ("contrast_value_" + number);
    contrast_value_id.innerHTML = contrast_value;

// update image
    fits.setContrast (fits.rois[number], contrast_value/100.0);
}

// called when the user makes a stretch selection
function onStretchSel() {
    fits.setStretch (gebi("stretch_sel").value);
}

// called when an ROI changes, roi is in image coords.
function onROIChange (roi, redef, moved) {
    var eid = gebi ('roiinfo_' + roi.z);
    var title = roi.z == 0 ? "Image" : "ROI " + roi.z;
    if(eid){
        displayStats (eid, "black", title, roi);
    }
    var dh = gebi ("roihcanvas_" + roi.z);
    if(dh){
        fits.displayHistogram (roi, dh);
    }
}

// called when user turns an ROI on or off
function onDisplayROI (roi_n) {
    var cb = gebi("display_roi_"+roi_n);
    fits.enableROI(roi_n, cb.checked);
}

// display roi and stats in an orderly manner in given DOM id in given color.
function displayStats (id, color, title, roi) {
    var stats = roi.stats;
    var fits_coords = fits.image2FITS(roi);
    var minat_coords = fits.image2FITS(roi.stats.minat);
    var maxat_coords = fits.image2FITS(roi.stats.maxat);
    id.innerHTML =
        title + ": " + pad(roi.width,4) + " x " + pad(roi.height,5)
          + " @ [" + pad(fits_coords.x,5) + ", "
          + pad(fits_coords.y,5) + "]<br>"
        + "Min " + pad(stats.min.toFixed(1),11) + pad("",4)
        + " @ [" + pad(minat_coords.x.toFixed(0),5) + ", "
        + pad(minat_coords.y.toFixed(0),5) + "]<br>"
        + "Max " + pad(stats.max.toFixed(1),11) + pad("",4)
        + " @ [" + pad(maxat_coords.x.toFixed(0),5) + ", "
        + pad(maxat_coords.y.toFixed(0),5) + "]<br>"
        + "Mean " + pad(stats.mean.toFixed(1),10) + pad("",2)
	+ "StdDev " + pad(stats.stddev.toFixed(1),12) + "<br>"
        + "Median " + pad(stats.median.toFixed(1),8) + pad("",1) 
        + " Sum " + pad(stats.sum.toFixed(1),15);
    id.style.color = color;
}

// return s padded on left to n chars
function pad (s, n) {
    s = s.toString();
    var nadd = n - s.length;
    for (var i = 0; i < nadd; i++)
        s = "&nbsp;" + s;
    return (s);
}


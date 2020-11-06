/* FITS "class".
 *
 * Version 2016-11-14
 *
 * This is a class to display a FITS files in a web page. The FITS file is loaded from an
 * ArrayBuffer, which can easily be obtained from either local or server based files. Once loaded we
 * can provide resizing, a roaming magnifying glass, a separate magnified window and multiple regions of
 * interest, all optional as desired.
 *
 * We provide no user interface controls, we only draw the image and associated graphics. You must
 * provide a div element in which we create and manage all required canvases as children. You may also 
 * specify an optional number of Regions of Interest. If you want to display stats or whatnot, you may
 * also ask us to invoke a callback when the mouse moves or an ROI changes.
 *
 * We create one canvas for the image, one for each ROI and one for the mag glass, in increasing z. If you
 * want access to these (can't think why you would) their ids are "roi_canvasN", where N runs from 0 through 
 * the number of requested ROIs, and "glass_canvas". Note roi_canvas0 is really just an immutable ROI the full
 * size of the image. The canvases are in order of increasing z-index, starting at 1 for the image and
 * ending with the glass at the highest z priotity so it is "on top".
 *
 * The location and stats for each ROI are in rois[], with rois[0] being the whole image. The stats within
 * each ROI determine only its own contrast except that the stats in the highest priority roi are also used
 * to determine the contrast for rois[0] (the whole image).
 *
 * Resizing was implemented by repurposing scrollbars.
 *
 * If anything goes wrong we throw a brief descriptive string.
 *
 *
 * Required minimal API:
 *
 *   var fits1 = new FITS (div_id, n_rois)
 *
 *     This call will instantiate a new FITS object within the given div id with the given number of ROIs.
 *     At this point the object does not contain an image (see next). Your typical div markup for a FITS
 *     display looks like this:
 *
 *        <div id="fits_div" 
 *           style='position:relative; resize:both; overflow:scroll;
 *             height:400px; width:400px; padding-right:17px; padding-bottom:17px' >
 *        </div>
 *
 *        where:
 *          * width and height are just initial since user may resize; they are also the minimums.
 *          * the padding mutes the scrollbars without effecting the mouse coords returned. The value 17
 *            depends on the browser but seems pretty common.
 *
 *     and the corresponding Javascript code would look like this:
 *
 *        var fits1 = new FITS (document.getElementById ("fits_div", 2);
 *
 *
 *   fits1.setNewImage (filename, ArrayBuffer)
 *
 *     install a new FITS file into the given FITS object. This may be done as many times as desired, each
 *     call overwriting the previous image.
 *
 *        filename: just a string used for error messages
 *        ArrayBuffer: the actual file contents, likely from a remote AJAX call or a local file selection.
 *
 *
 * Optional API:
 *
 *   fits1.addMouseHandler(myMouseHandler) 
 *     connect the given callback function for mouse moves. callback gets FITS loc{x,y} which can call
 *     getPixelAtFITS(loc) to get image coord.
 *
 *   fits1.addROIChangedHandler(myROIChangedHandler)
 *     connect the given callback function for ROI changes. callback gets three arguments:
 *       - roi{x,y,z,width,height,stats} where stats includes at least {min,max,mean,stddev,sum,sum2,npixels}
 *       - redef which is true iff the callback is being triggered because of a call to redefineROI().
 *       - moved which is true iff the callback is being triggered because the ROI was moved or resized.
 *
 *   fits1.addResizeHandler(myResizeListener)
 *     connect the given callback function for FITS display size changes.
 *
 *   fits1.addGlassCanvas(canvas_id)
 *     connect the given canvas into which we draw a magnified area surrounding the cursor location. If
 *     the user clicks the mouse over the image then subsequently moves the cursor outside the image, the
 *     clicked position is displayed.
 *
 *   fits1.setContrast(fits.rois[i], c)
 *     change contrast of image or ROI, where
 *       i: 0 = image, 1..nrois
 *       c: contrast, 0 <= c <= 1
 *
 *   fits1.setStretch (stretch)
 *     set desired stretch function, where stretch is currently one of "linear", "square" or "sqrt"
 *
 *   fits1.enableROI (roi_n, true_or_false)
 *     enable/disable a ROI given its rois[] index, ignored if out of bounds.
 *
 *   fits1.redefineROI (roi_n, roi_defn)
 *     given a ROI index (1 .. n_rois) move and/or resize the given ROI programmatically to the values in
 *     roi_defn which must contain {x,y,width,height}. Triggers addROIChangedHandler, if any, with redef
 *     and moved true. Throws if new definition is now wholy within the current image.
 *
 *   fits1.showHeader(force)
 *     display FITS header in a separate popup window if force, else only if already up
 *
 *   fits1.header.<key>
 *     access an individual header value, for example fits1.header.NAXIS1
 *
 *
 * The first pixel in a FITS file is to be displayed in the lower left corner. Javascript wants the
 * first pixel of an image to be the upper left corner. To accommodate this, FITS.setNewImage() flips
 * the pixel rows when filling the FITS.image array. Thus, displaying the image array with native Javascript
 * methods will display the pixels correctly. Then regarding pixel coordinates, FITS wants the lower left
 * corner to be [1,1] whereas Javascript wants the upper left to be [0,0]. All coordinates used in this
 * package use the Javascript convention. These may be converted to and from FITS using image2FITS() and
 * FITS2Image(). Note that ROIs will be adjusted so that the visual lower left corner will be the x,y
 * reference location in both coordinate systems.
 */


/* FITS view "class".
 * create an instance with new for each desired display area, fine to have more than one per page.
 */
function FITS (div_id, n_rois)
{

    // check args
    if (!div_id || div_id.tagName != "DIV")            // must be a div
    throw ("FITS requires a div");
    if (isNaN(parseInt(n_rois)))                // default to no ROIs
    n_rois = 0;

    // add a resize listener (see code at end)
    var thisfits = this;
    createResizeListener();
    addResizeListener (div_id, function() { thisfits.handleResize(); } );

    // build each ROI, including first one for the image
    this.rois = new Array(n_rois+1);
    // TODO: test for too few colors
    var roicolors = ["#bbb", "#55f", "#393", "orange", "#1ff", "#f1f", "#fa1", "white"];
    for (var i = 0; i <= n_rois; i++) {
    var roi = {};
    roi.x = 0;                        // ul roi x, image coords
    roi.y = 0;                        // ul roi y, image coords
    roi.z = i;                        // canvas z depth
    roi.enabled = true;                    // whether to display
    roi.width = 10000000;                    // roi width (start huge to force resize)
    roi.height = 10000000;                    // roi height (start huge to force resize)
    roi.contrast = 0;                    // display contrast, 0 .. 1
    roi.color = roicolors[i];                // border color
    roi.stats = {};                        // see computeROIStats()
    roi.black = undefined;                    // black pixel, once contrast is defined
    roi.white = undefined;                    // white pixel, once contrast is defined
    roi.cvs = FITS_newCanvas (div_id, "roi_canvas"+i, i+1);    // new canvas
    roi.ctx = roi.cvs.getContext("2d");            // handy canvas 2d context 
    this.rois[i] = roi;                    // add to array of all ROIs
    }

    // build the glass layer on top
    this.gcvs = FITS_newCanvas (div_id, "glass_canvas", n_rois+2); // glass canvas
    this.gctx = this.gcvs.getContext("2d");            // handy glass 2d context

    // connect our mouse and keyboard handlers
    window.addEventListener ("mousemove", function(event) { FITS_handleMouse (event, thisfits);}, true);
    window.addEventListener ("mousedown", function(event) { FITS_handleMouse (event, thisfits);}, true);
    window.addEventListener ("keydown", function(event) { FITS_handleKeyboard (event, thisfits);}, true);
    window.addEventListener ("keyup", function(event) { FITS_handleKeyboard (event, thisfits);}, true);

    // use highest priority roi for entire image contrast
    this.icroi = n_rois;

    // init instance variables, most are undefined until an image is set
    this.div_id = div_id;                    // canvases container
    this.image = undefined;                    // image, flipped in Y and phys values
    this.filename = undefined;                    // original FITS file name
    this.header = {};                        // FITS header index by keyword
    this.rawheader = [];                    // array of literal header cards
    this.drew_glass = false;                    // whether glass is currently visible
    this.glass_size = 0.05;                    // glass image fraction (before mag)
    this.glass_mag = 4;                        // default glass mag factor
    this.glass_mic = undefined;                    // center glass click location
    this.mic = undefined;                    // current mouse image coordinates
    this.width = undefined;                    // handy image size
    this.height = undefined;                    // handy image size
    this.resize_scale = undefined;                // display size / image size
    this.header_win = undefined;                // separate window for header
    this.stretch = "square";                    // default stretch

    // place to record user's callbacks
    this.userMouseHandler = undefined;                // user's mouse event callback
    this.userROIChangedHandler = undefined;            // user's ROI changed callback
    this.userGlassCanvas = undefined;                // user's canvas for drawing glass

    // ROI dragging state
    this.drag_roi = undefined;                    // rois[] index currently being dragged
    this.drag_code = undefined;                    // which edge, corner or all being dragged
    this.drag_mvos = {dx:0, dy:0};                // clicked move offset from roi center 
    this.cursors = {                        // map of drag_codes to javacript cursors
    "n-resize"  : "ns-resize",
    "s-resize"  : "ns-resize",
    "e-resize"  : "ew-resize",
    "w-resize"  : "ew-resize",
    "ne-resize" : "nesw-resize",
    "sw-resize" : "nesw-resize",
    "nw-resize" : "nwse-resize",
    "se-resize" : "nwse-resize",
    "move"      : "move"
    };
}

/* get fits from a url, by RDW */
FITS.prototype.imageFromUrl = function(fits_url)
{
    var xhr = new XMLHttpRequest();
    xhr.onload = function(e){
        result = xhr.response;
        if (xhr.status == 200){
            fits.setNewImage ('fits_file', result);
            fits.showHeader(false);
        }
    };

    xhr.open('GET', fits_url);
    xhr.responseType = 'arraybuffer';
    xhr.overrideMimeType("text/plain; charset=x-user-defined");
    xhr.send(null);
};

/* return a new canvas with z-index z with initial size same as parent.
 */
function FITS_newCanvas (parent, name, z)
{
    var cid = document.createElement ("canvas");
    cid.setAttribute ("id", name);

    cid.setAttribute ("style", "position:absolute; z-index:" + z);
    cid.setAttribute ("width", parseInt(parent.style.width));
    cid.setAttribute ("height", parseInt(parent.style.height));
    parent.appendChild (cid);

    return (cid);
}

/* capture the new FITS file from the given ArrayBuffer with the given name into roi[0].
 */
FITS.prototype.setNewImage = function (filename, fitsab) 
{
    // save file name
    this.filename = filename;

    // init header collections
    this.header = {};
    this.rawheader = [];

    // fill header from 80 byte cards blocked in units of 2880 bytes.
    var hlen = 0;

    try {
    for (hlen = 0; hlen < fitsab.byteLength; hlen += 80) {
        console.log(x);

        var card = String.fromCharCode.apply(null, new Uint8Array(fitsab, hlen, 80));
        if (card.match(/^END */)) {        // finished when see END
        hlen += 80;
        break;
        }

        this.rawheader.push(card);        // capture the raw card image

        if (card.indexOf ("=") < 0)        // skip COMMENT, HISTORY etc
        continue;

        var key = card.substring (0, 8);    // key is always the first 8 chars ...
        key = key.replace (/ *$/, "");    // without trailing blanks

        var val = card.substring (10);    // value starts in col 11 but ...
        val = val.replace (/^ */, "");    // remove leading blanks
        val = val.replace (/\/.*$/, "");    // remove comments
        val = val.replace (/ *$/, "");    // remove trailing blanks
        if (val.indexOf ("'") >= 0)        // looks like a string
        val = val.substring (1, val.length-2);
        else if (val.indexOf ("T") >= 0)    // looks like a True boolean
        val = true;
        else if (val.indexOf ("F") >= 0)    // looks like a False boolean
        val = false;
        else if (val.indexOf (".") >= 0)    // looks like a float
        val = parseFloat (val);
        else                // must be an int
        val = parseInt (val);
        this.header[key] = val;
        // console.log (key + ": #" + this.header[key] + "#");
     }
   } catch(e) {
     throw (this.filename + ": not a FITS file: " + e);
   }

    // confirm minimal header
    if (!(this.header.SIMPLE
        && typeof this.header.NAXIS1 == "number"
        && typeof this.header.NAXIS2 == "number"
        && typeof this.header.BITPIX == "number")) {
    throw (this.filename + ": not a valid FITS file");
    }

    // pixels start on next whole 2880 block
    if ((hlen%2880) > 0)
    hlen += 2880 - (hlen%2880);

    // save image size
    // console.log (this.header.NAXIS1 + " x " + this.header.NAXIS2 + " x " + this.header.BITPIX);
    this.width = this.rois[0].width = this.header.NAXIS1;
    this.height = this.rois[0].height = this.header.NAXIS2;
    var npixels = this.width * this.height;
    var nbytes = npixels * Math.abs(this.header.BITPIX)/8;
    if (fitsab.byteLength < hlen + nbytes)
    throw (this.filename + ": too short: " + fitsab.byteLength + " < " + (hlen + nbytes));
    // console.log (npixels + " pixels in " + nbytes + " bytes");

    // convert remainder of file to an array of physical values, depending on type.
    // along the way also flip vertically.
    var bzero = this.header.BZERO || 0;
    var bscale = this.header.BSCALE || 1;
    this.image = new Array (npixels);
    var dv = new DataView (fitsab, hlen, nbytes);
    if (this.header.BITPIX == 8) {
    // data is array of unsigned bytes
    var imgi = 0;
    for (var y = 0; y < this.height; y++) {
        var fitsi = (this.height-1-y)*this.width;
        for (var x = 0; x < this.width; x++) {
        this.image[imgi] = bzero + bscale*dv.getUint8(fitsi);
        imgi++;
        fitsi++;
        }
    }
    } else if (this.header.BITPIX == 16) {
    // data is array of signed words, big endian
    var imgi = 0;
    for (var y = 0; y < this.height; y++) {
        var fitsi = (this.height-1-y)*this.width;
        for (var x = 0; x < this.width; x++) {
        this.image[imgi] = bzero + bscale*dv.getInt16 (fitsi*2, false);
        imgi++;
        fitsi++;
        }
    }
    } else if (this.header.BITPIX == 32) {
    // data are array of signed double words, big endian
    var imgi = 0;
    for (var y = 0; y < this.height; y++) {
        var fitsi = (this.height-1-y)*this.width;
        for (var x = 0; x < this.width; x++) {
        this.image[imgi] = bzero + bscale*dv.getInt32 (fitsi*4, false);
        imgi++;
        fitsi++;
        }
    }
    } else if (this.header.BITPIX == -32) {
    // data are array of IEEE single precising floating point, big endian
    var imgi = 0;
    for (var y = 0; y < this.height; y++) {
        var fitsi = (this.height-1-y)*this.width;
        for (var x = 0; x < this.width; x++) {
        this.image[imgi] = bzero + bscale*dv.getFloat32 (fitsi*4, false);
        imgi++;
        fitsi++;
        }
    }
    } else {
    throw (this.filename + ": BITPIX " + this.header.BITPIX + " is not yet supported");
    }


    // display by faking a resize event which does everything
    this.handleResize();
}


/* called to display the FITS header in its own window.
 * if force is true, we create a new window; if false, we only update the header window if it already
 * exists and is still open.
 */
FITS.prototype.showHeader = function(force)
{
    // check null cases
    if (!this.filename || !this.rawheader)
    return;        // no image yet
    var isup = this.header_win && !this.header_win.closed;
    if (!isup && !force)
    return;        // not up but don't care

    // create window if it does not exist or last one was closed
    if (this.header_win == undefined || this.header_win.closed) {
    this.header_win = window.open("", "_blank", "width=500, height=500, scrollbars=yes");
    // build outer html element in document, then updates go inside this
    this.header_win.document.write ("<html></html>");
    }

    // build text that will go inside html element
    var text = "<head><title>" + this.filename + " Header</title></head><body><pre>";
    for (var i = 0; i < this.rawheader.length; i++)
        text += this.rawheader[i] + "<br>";
    text += "</pre></body>";

    // display
    this.header_win.document.documentElement.innerHTML = text;
}


/* compute some image stats at the given ROI.
 * ROI must have x, y, width and height.
 * object returned will have at least properties npixels, min, max, sum, mean, stddev and histo.
 * throw if ROI is not wholly contained with in the image.
 */
FITS.prototype.computeROIStats = function (roi)
{
    if (!this.image)
    return;

    // console.log (roi.x + " " + roi.y + " " + roi.width + " " + roi.height);
    if (roi.x < 0 || roi.width < 0 || roi.x+roi.width > this.width
              || roi.y < 0 || roi.height < 0 || roi.y+roi.height > this.height)
    throw (this.filename + ": roi is outside image [" + roi.x + "," + roi.y + "], "
        + roi.width + " x " + roi.height);

    // scan pixels within roi
    var npixels = roi.width*roi.height;
    var pxi = roi.y*this.width + roi.x;        // start of first row in roi
    var min = this.image[pxi];
    var max = min;
    var maxatx = roi.x, maxaty = roi.y;
    var minatx = roi.x, minaty = roi.y;
    var sum = 0;
    var sum2 = 0;
    for (var dy = 0; dy < roi.height; dy++) {
    for (var dx = 0; dx < roi.width; dx++) {
        var p = this.image[pxi++];
        if (p < min) {
            min = p;
        minatx = dx + roi.x;
        minaty = dy + roi.y;
        }
        if (p > max) {
        max = p;
        maxatx = dx + roi.x;
        maxaty = dy + roi.y;
        }
        sum += p;
        sum2 += p*p;
    }
    pxi += (this.width - roi.width);    // skip to start of next row
    }
    var range = Math.max (1, max - min);
    var stddev = Math.sqrt (npixels*sum2 - sum*sum)/npixels;

    // init histogram, index N bins as [0..N-1] for pixel values [min..max].
    // nothing critical about N.
    var histo = new Array (128);
    for (var i = 0; i < histo.length; i++)
    histo[i] = 0;

    // use pixel range to rescan for histogram
    pxi = roi.y*this.width + roi.x;        // start of first row in roi
    var histomax = 0;                // n counts in largest bin
    for (var dy = 0; dy < roi.height; dy++) {
    for (var dx = 0; dx < roi.width; dx++) {
        var p = this.image[pxi++];
        var bin = Math.floor((histo.length-1)*(p - min)/range);
        if (++histo[bin] > histomax)
        histomax = histo[bin];
    }
    pxi += (this.width - roi.width);    // skip to start of next row
    }

    // find median: pixel at which half are below and half above
    var histi = 0;
    for (var count = 0; count < npixels/2; histi++)
    count += histo[histi];
    var median = Math.floor(min + range*histi/histo.length);
    // console.log ('median = ' + median);

    // return the stats report
    return {
    npixels     : npixels,            // n pixels in this roi
    min     : min,                // smallest pixel in this roi
    minat     : { x: minatx,            // location of smallest pixel
             y: minaty
           },
    max     : max,                // largest pixel in this roi
    maxat     : { x: maxatx,            // location of largest pixel
             y: maxaty
           },
    range    : range,            // large of 1 and (max - min)
    sum     : sum,                // sum of all pixels in this roi
    mean     : sum/npixels,            // average of all pixels in this roi
    median   : median,            // median of all pixels in this roi
    stddev     : stddev,            // stddev of all pixels in this roi
    histo     : histo,            // histogram, count of min .. max in length bins
    histomax : histomax,            // greatest count in histo, used for scaling
    };
}

/* set contrast from 0 .. 1 on the given roi then redraw.
 */
FITS.prototype.setContrast = function (roi, contrast)
{
    if (!this.image)
    return;
    if (contrast < 0 || contrast > 1)
    throw ("setContrast " + contrast + " must be 0 .. 1");
    roi.contrast = Math.sqrt(contrast);        // more control near high contrast
    this.renderROI (roi, false, false);
}


/* return black white pixel values given contrast and stats.
 */
FITS.prototype.findBlackAndWhite = function (contrast, stats)
{
    if (!stats)
    return;

    // handy
    var histo = stats.histo;
    var black, white;

    // pick one
    if (true) {

    // stddev method

    black = Math.max (stats.min, stats.mean - 6*stats.stddev*(1-contrast));
    white = Math.min (stats.max, stats.mean + 6*stats.stddev*(1-contrast));

    } else if (false) {

    // median spread method sans outer 1%

        var NFRACP = stats.npixels/50;
    var nhisto = histo.length - 1;
        var blacki = 0, whitei = nhisto;
        for (var sum = 0; blacki < nhisto && sum < NFRACP; blacki++)
            sum += histo[blacki];
        for (var sum = 0; whitei >= 0 && sum < NFRACP; --whitei)
            sum += histo[whitei];

    var minpix = stats.min + blacki*stats.range/nhisto;
    var maxpix = stats.min + whitei*stats.range/nhisto;

    black = stats.median - (stats.median - minpix)*(1-contrast);
    white = stats.median + (maxpix - stats.median)*(1-contrast);

    } else if (false) {

    // spread equal fraction about the median to each end

    black = stats.median - (stats.median - stats.min)*(1-contrast);
    white = stats.median + (stats.max - stats.median)*(1-contrast);

    // console.log(stats.min + ' .. ' + stats.median + ' .. ' + stats.max + ' : ' + black + ' .. ' + white);

    } else if (false) {

    // spread equally about the median by smaller of distance to each end

    var spread = Math.min (stats.max - stats.median, stats.median - stats.min);
    black = stats.median - spread*(1-contrast);
    white = stats.median + spread*(1-contrast);

    } else {

    // contrast is based on displaying some fraction of total pixels about the median

    var median_i = Math.floor(histo.length*(stats.median-stats.min)/stats.range);
    var contrast_count = stats.npixels * (1-contrast);

    var black_i = Math.max (median_i-1, 0);
    var white_i = Math.min (median_i+1, histo.length-1);
    for (var count = histo[median_i]; count < contrast_count; ) {
        count += histo[black_i];
        count += histo[white_i];
        black_i = Math.max (black_i-1, 0);
        white_i = Math.min (white_i+1, histo.length-1);
    }

    black = stats.min + stats.range*black_i/histo.length;
    white = stats.min + stats.range*white_i/histo.length;
    }

    // insure constant has some depth
    // if (black >= white)
    // black = white - 1;

    return {
    black : black,
    white : white
    };

}


// called when user resizes the div containing the canvases
FITS.prototype.handleResize = function()
{
    if (!this.image)
    return;

    // get current physical size of div, accommodate possible units suffix
    var divw = parseInt(this.div_id.style.width);
    var divh = parseInt(this.div_id.style.height);

    // resize each canvas to match the div, glass too
    for (var i = 0; i < this.rois.length; i++) {
    this.rois[i].cvs.setAttribute ("width", divw);
    this.rois[i].cvs.setAttribute ("height", divh);
    }
    this.gcvs.setAttribute ("width", divw);
    this.gcvs.setAttribute ("height", divh);

    // establish size of canvas compared to size of image, maintaining aspect ratio
    if (divw/divh > this.width/this.height) {
    // full height
    this.resize_scale = divh/this.height;
    } else {
    // full width
    this.resize_scale = divw/this.width;
    }

    // set each roi scale so we can always work in image coords, glass too
    for (var i = 0; i < this.rois.length; i++) {
    this.rois[i].ctx.setTransform (1, 0, 0, 1, 0, 0);
    this.rois[i].ctx.translate (0.5, 0.5);        // crisper lines and pixels
    this.rois[i].ctx.scale (this.resize_scale, this.resize_scale);
    }
    this.gctx.setTransform(1, 0, 0, 1, 0, 0);
    this.gctx.translate (0.5, 0.5);        // crisper lines and pixels
    this.gctx.scale (this.resize_scale, this.resize_scale);

    // now render everything at this size
    this.renderAll();
}


// (re)render everything, be prepared to adjust ROIs and glass sizes
FITS.prototype.renderAll = function()
{
    // update all ROIS first so rois[0] can use stats in rois[icroi] for contrast
    var nrois = this.rois.length;
    var moved = false;
    for (var i = 0; i < nrois; i++) {
    var roi = this.rois[i];

    // adjust ROI back to a default location inside if it is now outside the image size
    if (roi.x + roi.width > this.width || roi.y + roi.height > this.height
        || (roi.width*this.resize_scale < 20 && roi.height*this.resize_scale < 20)) {
        roi.x = Math.floor(3*((nrois-i)%nrois)*this.width/20);    // left->right decreasing z
        roi.y = Math.floor(this.height/20);
        roi.width = Math.floor(this.width/10);
        roi.height = Math.floor(this.height/10);
        moved = true;
    }
    }

    // now render all rois
    for (var i = 0; i < this.rois.length; i++)
    this.renderROI(this.rois[i], false, moved);
}

// allow user to set desired stretch function
FITS.prototype.setStretch = function (s)
{
    this.stretch = s;
    this.renderAll();
}


// allow user to enable/disable a given roi
FITS.prototype.enableROI = function (roi_n, enable)
{
    if (roi_n < 1 || roi_n >= this.rois.length)
    throw ('enableROI(' + roi_n + ') must be 1 .. ' + (this.rois.length-1));

    var roi = this.rois[roi_n];
    roi.enabled = enable;
    this.renderROI (roi, false, false);
}

/* redefine the given ROI.
 * throw if not wholy within the current image.
 */
FITS.prototype.redefineROI = function (roi_n, roi_defn)
{
    // validate roi_n
    if (roi_n < 1 || roi_n >= this.rois.length)
    throw ('redefineROI(' + roi_n + ') must be 1 .. ' + (this.rois.length-1));

    // validate roi_defn
    if (roi_defn.x < 0 || roi_defn.x + roi_defn.width > this.width 
        || roi_defn.y < 0 || roi_defn.y + roi_defn.height > this.height)
    throw ('redefineROI [' + roi_defn.x + ',' + roi_defn.y + ';' + roi_defn.width + 'x' + roi_defn.height
           + '] not inside image [' + this.width + 'x' + this.height + ']');

    var roi = this.rois[roi_n];

    // install new definition
    roi.x = roi_defn.x;
    roi.y = roi_defn.y;
    roi.width = roi_defn.width;
    roi.height = roi_defn.height;

    // console.log ('redefineROI to ['+ roi.x + ',' + roi.y + ';' + roi.width + 'x' + roi.height + ']');

    // redraw and indicate this is a move
    this.renderROI(roi, true, true);

    // also redisplay image if we moved rois[this.icroi]
    if (this.rois.length > 1 && roi == this.rois[this.icroi])
    this.renderROI(this.rois[0], false, false);
}


/* render the given ROI and invoke userROIChangedHandler, if any, with redef
 */
FITS.prototype.renderROI = function (roi, redef, moved)
{
    // harmless if no image yet
    if (!this.image)
    return;

    // compute our stats
    roi.stats = this.computeROIStats (roi);
    
    // find black and white.
    var bw = this.findBlackAndWhite (roi.contrast, roi.stats);
    var black = roi.black = bw.black;
    var white = roi.white = bw.white;

    // N.B.: whole image in rois[0] uses stats from rois[icroi]
    if (roi == this.rois[0] && this.rois.length > 1 && this.rois[this.icroi].enabled) {
    var icroi_stats = this.computeROIStats (this.rois[this.icroi]);
    var bw = this.findBlackAndWhite (roi.contrast, icroi_stats);
    black = bw.black;
    white = bw.white;
    }

    // handy
    var ctx = roi.ctx;
    var range = Math.max (1, white - black);

    // set up stretch option
    var stretch_f;
    if (this.stretch == "linear") {
    stretch_f = function (pixel) {
        return (255*(pixel-black)/range);
    }
    } else if (this.stretch == "square") {
    stretch_f = function (pixel) {
        var v = (pixel-black)/range;
        return (255*v*v);
    }
    } else if (this.stretch == "sqrt") {
    stretch_f = function (pixel) {
        return (255*Math.sqrt((pixel-black)/range));
    }
    } else {
    throw ("Unknown stetch: " + this.stretch + ", choices are linear, square and sqrt");
    }


    // render as gray scale from black to white, or all transparent if disabled
    if (roi.enabled) {
    var roiimage = new ImageData (roi.width, roi.height);
    var roidata = roiimage.data;        // detach from DOM for potentially faster access?
    var datai = 0;                // RGBA tuple index
    for (var y = roi.y; y < roi.y + roi.height; y++) {
        for (var x = roi.x; x < roi.x + roi.width; x++) {
        var p = this.image[y*this.width + x];
        var gray = stretch_f (p);
        roidata[4*datai]   = gray;    // red
        roidata[4*datai+1] = gray;    // green
        roidata[4*datai+2] = gray;    // blue
        roidata[4*datai+3] = 255;    // alpha
        datai++;
        }
    }
    roiimage.data = roidata;            // reattach

    // display it, must go through a temp canvas in order to use drawImage
    var tempcan = document.createElement ("canvas");
    tempcan.width = roi.width;
    tempcan.height = roi.height;
    var tcctx = tempcan.getContext("2d");
    tcctx.putImageData (roiimage, 0, 0);
    this.clearLayer (ctx);
    noSmoothing (ctx);
    ctx.drawImage (tempcan, roi.x, roi.y);    // resizes according to ctx

    // garbage collector will clean up tempcvs because it has no parent but give it a kick anyway
    tempcan = undefined;

    // add outline
    ctx.strokeStyle = roi.color;
    ctx.lineWidth = 2;
    ctx.beginPath();
        ctx.moveTo (roi.x, roi.y);
        ctx.lineTo (roi.x+roi.width, roi.y);
        ctx.lineTo (roi.x+roi.width, roi.y+roi.height);
        ctx.lineTo (roi.x, roi.y+roi.height);
        ctx.lineTo (roi.x, roi.y);
        ctx.lineTo (roi.x+roi.width, roi.y);    // fill corner if highly magnified
    ctx.stroke();
    } else {
    this.clearLayer (ctx);
    }

    // inform user if interested
    if (this.userROIChangedHandler != undefined)
    this.userROIChangedHandler (roi, redef, moved);
}



/* given image coords of glass center, draw a magnified portion on the glass canvas
 */
FITS.prototype.renderGlass = function (image_loc)
{
    // harmless if called without a glass canvas or before image is loaded
    if (!image_loc || !this.gcvs || !this.image)
    return;

    // check for edges

    var glassimgsz = this.glass_size * this.width;
    var glasssz = glassimgsz * this.glass_mag;
    var ulglassx, ulglassy, glassw, glassh, imw, imh;
    var x = image_loc.x;
    var y = image_loc.y;

    if (x < 0 || x >= this.width)
    return;
    if (x < glasssz/2) {
    ulglassx = 0;
    glassw = 2*x;
    imw = glassw/this.glass_mag;
    } else if (x > this.width - glasssz/2) {
    glassw = 2*(this.width - x);
    ulglassx = this.width - glassw;
    imw = glassw/this.glass_mag;
    } else {
    ulglassx = x - glasssz/2;
    glassw = glasssz;
    imw = glassimgsz;
    }

    if (y < 0 || y >= this.height)
    return;
    if (y < glasssz/2) {
    ulglassy = 0;
    glassh = 2*y;
    imh = glassh/this.glass_mag;
    } else if (y > this.height - glasssz/2) {
    glassh = 2*(this.height - y);
    ulglassy = this.height - glassh;
    imh = glassh/this.glass_mag;
    } else {
    ulglassy = y - glasssz/2;
    glassh = glasssz;
    imh = glassimgsz;
    }

    // draw glass in canvas from image layer with magnified size
    noSmoothing (this.gctx);
    this.gctx.drawImage (this.rois[0].cvs,                    // source canvas
            (x-imw/2)*this.resize_scale+1, (y-imh/2)*this.resize_scale+1,    // source x, y
        imw*this.resize_scale, imh*this.resize_scale,            // source w, h
        ulglassx, ulglassy,                        // dest (gid_ctx) x, y
        glassw, glassh);                        // dest w, h

    // add a nice border
    this.gctx.strokeStyle = "yellow";
    this.gctx.beginPath();
    this.gctx.moveTo (ulglassx, ulglassy);
    this.gctx.lineTo (ulglassx+glassw, ulglassy);
    this.gctx.lineTo (ulglassx+glassw, ulglassy+glassh);
    this.gctx.lineTo (ulglassx, ulglassy+glassh);
    this.gctx.lineTo (ulglassx, ulglassy);
    this.gctx.stroke();
}


/* convert image to FITS coords.
 * if the given object contains at least {x, y, height} then return a copy of the object with x and y
 *   converted to FITS coordinates, including arranging for new reference corner to be visually in the
 *   lower left corner, ie, at smallest numeric location.
 * if the given object contains x and y but not height, then return a copy of the object with just x
 *   and y converted to FITS coords without regard to a reference position.
 * N.B. we do no bounds checking
 */
FITS.prototype.image2FITS = function (imageloc)
{
    // skip if no image yet
    if (!this.height || !imageloc)
    return;

    var fitsloc = (JSON.parse(JSON.stringify(imageloc)));
    fitsloc.x = imageloc.x + 1;
    fitsloc.y = this.height - imageloc.y;
    if (imageloc.height)
    fitsloc.y -= (imageloc.height-1);        // exclusive
    return (fitsloc);
}

/* convert FITS to image coords.
 * if the given object contains at least {x, y, height} then return a copy of the object with x and y
 *   converted to image coordinates, including arranging for new reference corner to be visually in the
 *   lower left corner, ie, at smallest numeric location.
 * if the given object contains x and y but not height, then return a copy of the object with just x
 *   and y converted to FITS coords without regard to a reference position.
 * N.B. we do no bounds checking
 */
FITS.prototype.FITS2Image = function (fitsloc)
{
    // skip if no image yet
    if (!this.height || !fitsloc)
    return;

    var imageloc = (JSON.parse(JSON.stringify(fitsloc)));
    imageloc.x = fitsloc.x - 1;
    imageloc.y = this.height - fitsloc.y;
    if (fitsloc.height)
    imageloc.y -= (fitsloc.height-1);        // exclusive
    return (imageloc);
}


/* convert screen coords in a javascript event to image coords
 */
FITS.prototype.event2image = function (event)
{
    var imgcoords = {};

    // get raw coords, depending on browser
    if (event.pageX) {
    imgcoords.x = event.pageX;
    imgcoords.y = event.pageY;
    } else {
    imgcoords.x = event.clientX;
    imgcoords.y = event.clientY;
    }

    // account for browser window scrolling (not the div scrolling)
    var iid_rect = this.rois[0].cvs.getBoundingClientRect();
    imgcoords.x -= (window.pageXOffset + iid_rect.left);
    imgcoords.y -= (window.pageYOffset + iid_rect.top);

    // now account for user resizing and drop to nearest whole pixel
    imgcoords.x = Math.floor(imgcoords.x/this.resize_scale);
    imgcoords.y = Math.floor(imgcoords.y/this.resize_scale);

    return (imgcoords);
}


/* function user can call to register a function we call whenever the mouse moves over the image,
 *   or cancel same if undefined.
 * if we do call handler, first argument will be a object containing x and y in FITS coords, second will be
 *   value of pixel at that location.
 */
FITS.prototype.addMouseHandler = function (handler)
{
    this.userMouseHandler = handler;
}


/* function user can call to register a function we call whenever an ROI changes location or shape,
 *   or cancel same if undefined.
 * if we do call handler, argument will be an object with ROI details.
 */
FITS.prototype.addROIChangedHandler = function (handler)
{
    this.userROIChangedHandler = handler;
}


/* function user can call to register a function we call whenever the FITS canvases are resized
 */
FITS.prototype.addResizeHandler = function (handler)
{
    addResizeListener (this.div_id, handler);
}
 


/* function user can call to register a canvas on which we draw a magnified region centered under 
 *   the cursor, or undefined to cancal this feature.
 */
FITS.prototype.addGlassCanvas = function (canvas_id)
{
    this.userGlassCanvas = canvas_id;
}


/* given an image location, set this.drag_roi and this.drag_code, if any.
 * don't worry too much about resolving ambiguities if some ROIs overlap.
 */
FITS.prototype.findROI = function (image_loc)
{
    var stol = 4;                    // tolerance, in screen pixels
    var tolerance = stol/this.resize_scale;        // tolerance, in image pixels

    this.drag_roi = undefined;
    this.drag_code = undefined;

    // don't include the basic image in ROI 0
    for (var i = 1; this.drag_code == undefined && i < this.rois.length; i++) {
    var roi = this.rois[i];

    var near = roi.enabled
        && image_loc.x > roi.x - tolerance && image_loc.x < roi.x + roi.width + tolerance
        && image_loc.y > roi.y - tolerance && image_loc.y < roi.y + roi.height + tolerance

    if (near) {

        var on_top_edge = image_loc.y < roi.y + tolerance;

        var want_move = on_top_edge && Math.abs(image_loc.x - (roi.x + roi.width/2)) < roi.width/6;

        if (want_move)
        this.drag_code = "move";
        else {
        var on_left_edge   = image_loc.x < roi.x + tolerance;
        var on_right_edge  = image_loc.x > roi.x + roi.width - tolerance;
        var on_bottom_edge = image_loc.y > roi.y + roi.height - tolerance;
        if (on_left_edge) {
            if (on_top_edge)
            this.drag_code = "nw-resize";
            else if (on_bottom_edge)
            this.drag_code = "sw-resize";
            else
            this.drag_code = "w-resize";
        } else if (on_right_edge) {
            if (on_top_edge)
            this.drag_code = "ne-resize";
            else if (on_bottom_edge)
            this.drag_code = "se-resize";
            else
            this.drag_code = "e-resize";
        } else if (on_top_edge) {
            if (on_left_edge)
            this.drag_code = "nw-resize";
            else if (on_right_edge)
            this.drag_code = "ne-resize";
            else
            this.drag_code = "n-resize";
        } else if (on_bottom_edge) {
            if (on_left_edge)
            this.drag_code = "sw-resize";
            else if (on_right_edge)
            this.drag_code = "se-resize";
            else
            this.drag_code = "s-resize";
        }
        }

        if (this.drag_code != undefined)
        this.drag_roi = i;
    }
    }
}


/* update the position of the drag_roi to the given image loc
 */
FITS.prototype.moveROI = function (image_loc)
{
    var roi = this.rois[this.drag_roi];
    var new_code = undefined;

    if (this.drag_code == "move") {
    // draw ROI centered at image_loc
    // beware fractional x or y when roi width is odd
    roi.x = Math.min (Math.max (0,image_loc.x + this.drag_mvos.dx - Math.round(roi.width/2+0.5)),
                this.width - roi.width);
    roi.y = Math.min (Math.max (0,image_loc.y + this.drag_mvos.dy - Math.round(roi.height/2+0.5)),
                this.height - roi.height);

    } else if (this.drag_code == "n-resize") {
    var dy = image_loc.y - roi.y;
    roi.y += dy;
    roi.height -= dy;
    if (roi.height < 0)
        new_code = 's-resize';

    } else if (this.drag_code == "s-resize") {
    roi.height += image_loc.y - (roi.y + roi.height);
    if (roi.height < 0)
        new_code = 'n-resize';

    } else if (this.drag_code == "e-resize") {
    roi.width += image_loc.x - (roi.x + roi.width);
    if (roi.width < 0)
        new_code = 'w-resize';

    } else if (this.drag_code == "w-resize") {
    var dx = image_loc.x - roi.x;
    roi.x += dx;
    roi.width -= dx;
    if (roi.width < 0)
        new_code = 'e-resize';

    } else if (this.drag_code == "ne-resize") {
    roi.width += image_loc.x - (roi.x + roi.width);
    var dy = image_loc.y - roi.y;
    roi.y += dy;
    roi.height -= dy;
    if (roi.width < 0 && roi.height < 0)
        new_code = 'sw-resize';
    else if (roi.width < 0)
        new_code = 'nw-resize';
    else if (roi.height < 0)
        new_code = 'se-resize';

    } else if (this.drag_code == "se-resize") {
    roi.width += image_loc.x - (roi.x + roi.width);
    roi.height += image_loc.y - (roi.y + roi.height);
    if (roi.width < 0 && roi.height < 0)
        new_code = 'nw-resize';
    else if (roi.width < 0)
        new_code = 'sw-resize';
    else if (roi.height < 0)
        new_code = 'ne-resize';

    } else if (this.drag_code == "nw-resize") {
    var dy = image_loc.y - roi.y;
    roi.y += dy;
    roi.height -= dy;
    var dx = image_loc.x - roi.x;
    roi.x += dx;
    roi.width -= dx;
    if (roi.width < 0 && roi.height < 0)
        new_code = 'se-resize';
    else if (roi.width < 0)
        new_code = 'ne-resize';
    else if (roi.height < 0)
        new_code = 'sw-resize';

    } else if (this.drag_code == "sw-resize") {
    var dx = image_loc.x - roi.x;
    roi.x += dx;
    roi.width -= dx;
    roi.height += image_loc.y - (roi.y + roi.height);
    if (roi.width < 0 && roi.height < 0)
        new_code = 'ne-resize';
    else if (roi.width < 0)
        new_code = 'se-resize';
    else if (roi.height < 0)
        new_code = 'nw-resize';
    }

    if (new_code != undefined) {
    if (roi.width < 0 && roi.height < 0) {
        roi.x += roi.width;
        roi.width = -roi.width;
        roi.y += roi.height;
        roi.height = -roi.height;
        this.drag_code = new_code;
    } else if (roi.width < 0) {
        roi.x += roi.width;
        roi.width = -roi.width;
        this.drag_code = new_code;
    } else if (roi.height < 0) {
        roi.y += roi.height;
        roi.height = -roi.height;
        this.drag_code = new_code;
    }
    }

    // avoid 0 size
    if (roi.width == 0)
    roi.width = 1;
    if (roi.height == 0)
    roi.height = 1;

    // display
    this.renderROI(roi, false, true);

    // also redisplay image if we moved rois[this.icroi]
    if (this.rois.length > 1 && roi == this.rois[this.icroi])
    this.renderROI(this.rois[0], false, false);
}


/* clear the given canvas context
 */
FITS.prototype.clearLayer = function (ctx)
{
    // ctx is already scaled to accept image coords
    ctx.clearRect (0, 0, this.width, this.height);
}


/* our keyboard handler, much like a regular listener but includes the context FITS object in
 *   addition to the usual javascript event.
 * basically just record state changes for mag glass etc.
 * nice tutortial: http://javascript.info/tutorial/keyboard-events
 */
function FITS_handleKeyboard (e, thisfits)
{
    e = e || event;

    thisfits.showGlass = e.shiftKey;
//    thisfits.updateGlass ();
}


/* our real mousemove handler, much like a regular listener but includes the context FITS object in
 *   addition to the usual javascript event.
 * handles the glass and ROIs, if any, and calls user's callbacks, if any
 */
function FITS_handleMouse (event, thisfits)
{
    // ignore until image is defined
    if (!thisfits.image)
    return;

    // get image coords of mouse
    var mic = thisfits.event2image (event);

    // check whether over image
    var over = (mic.x >= 0 && mic.x < thisfits.width
            && mic.y >= 0 && mic.y < thisfits.height);

    // if not over, just render glass and update mouse loc at last known location
    if (!over) {
    if (thisfits.glass_mic) {
        thisfits.mic = thisfits.glass_mic;
//        thisfits.updateGlass ();
    }
    // call user mouse moved callback, if any  TODO??
    // if (thisfits.userMouseHandler != undefined)
        // thisfits.userMouseHandler (thisfits.mic);
    return;
    }

    // record as current valid location
    thisfits.mic = mic;

    // update glass, if any
//    thisfits.updateGlass ();
}

/* function user can call to get value of pixel at any FITS coordinate.
 * we return 0 if location is undefined or not valid
 */
FITS.prototype.getPixelAtFITS = function (fitsloc)
{
    if (fitsloc == undefined)
    return 0;
    var imageloc = this.FITS2Image (fitsloc);
    if (imageloc.x >= 0 && imageloc.x < this.width && imageloc.y >= 0 && imageloc.y < this.height)
    return this.image[imageloc.y*this.width + imageloc.x];
    else
    return 0;
}

/* given an ROI and a canvas ID, display a histogram of the image pixels.
 * TODO: add tick marks
 */
FITS.prototype.displayHistogram = function (roi, canvas_id)
{
    // handy
    var ctx = canvas_id.getContext ("2d");
    var graphw = canvas_id.width;
    var graphh = canvas_id.height;
    var stats = roi.stats;
    var histo = stats.histo;
    var lhmax = Math.log(stats.histomax);

    // crisper without smoothing and coords centered on display pixels
    noSmoothing(ctx);
    ctx.setTransform (1, 0, 0, 1, 0, 0);
    ctx.translate (0.5, 0.5);

    // background
    ctx.fillStyle = '#888';
    ctx.fillRect (0, 0, graphw, graphh);

    // draw histogram, depending on sparse or rich
    if (graphw > histo.length) {
    // connect shape across histogram
    ctx.fillStyle = roi.color;
    ctx.beginPath();
        ctx.moveTo (0, graphh-1);
        for (var hx = 0; hx < histo.length; hx++) {
        var x = Math.floor(graphw*hx/histo.length);
        var y = (histo[hx] > 1) ? Math.floor(graphh*(1.0 - Math.log(histo[hx])/lhmax)) : graphh-1;
        ctx.lineTo (x, y);
        }
        ctx.lineTo (graphw, graphh-1);
        ctx.lineTo (0, graphh-1);
    ctx.fill();
    } else {
    // draw every x
    ctx.fillStyle = roi.color;
    ctx.beginPath();
        ctx.moveTo (0, graphh-1);
        for (var x = 0; x < graphw; x++) {
        var hx = Math.floor(x*histo.length/graphw);
        var y = (histo[hx] > 1) ? Math.floor(graphh*(1.0 - Math.log(histo[hx])/lhmax)) : graphh-1;
        ctx.lineTo (x, y);
        }
        ctx.lineTo (graphw, graphh-1);
        ctx.lineTo (0, graphh-1);
    ctx.fill();
    }

    // draw border
    ctx.strokeStyle = "black";
    ctx.beginPath();
    ctx.moveTo (0, 0);
    ctx.lineTo (0, graphh);
    ctx.lineTo (graphw, graphh);
    ctx.lineTo (graphw, 0);
    ctx.lineTo (0, 0);
    ctx.stroke();

    // mark the contrast limits

    ctx.strokeStyle = "#aa44aa";            // "median" and "magenta" start with m
    ctx.beginPath();
    var medianx = Math.floor((graphw-1)*(stats.median - stats.min)/stats.range);
    ctx.moveTo (medianx, 0);
    ctx.lineTo (medianx, graphh-1);
    ctx.stroke();

    ctx.strokeStyle = "#44aa44";            // "green" rhythms with "mean"
    ctx.beginPath();
    var meanx = Math.floor((graphw-1)*(stats.mean - stats.min)/stats.range);
    ctx.moveTo (meanx, 0);
    ctx.lineTo (meanx, graphh-1);
    ctx.stroke();

    ctx.strokeStyle = "black";
    ctx.beginPath();
    var blackx = Math.floor((graphw-1)*(roi.black - stats.min)/stats.range);
    ctx.moveTo (blackx, 0);
    ctx.lineTo (blackx, graphh-1);
    ctx.stroke();

    ctx.strokeStyle = "white";
    ctx.beginPath();
    var whitex = Math.floor((graphw-1)*(roi.white - stats.min)/stats.range);
    ctx.moveTo (whitex, 0);
    ctx.lineTo (whitex, graphh-1);
    ctx.stroke();

    // console.log('x: ' + blackx + ' .. ' + whitex + ' about ' + medianx);
    // console.log('p: ' + roi.black + ' .. ' + roi.white + ' about ' + stats.median);
}

/* disable image smoothing on the given canvas conext.
 * still experimental
 */
function noSmoothing(ctx)
{
    ctx.imageSmoothingEnabled = false;
    ctx.mozImageSmoothingEnabled = false;

}


/* The following wonderous bit of magic is from
 *   http://www.backalleycoder.com/2013/03/18/cross-browser-event-based-element-resize-detection
 * It creates the document function addResizeListener that connects a callback called whenever an element
 * is resized. It's unfortunate such as basic facility was not already provided.
 */
function createResizeListener ()
{
  var attachEvent = document.attachEvent;
  var isIE = navigator.userAgent.match(/Trident/);
  var requestFrame = (function(){
    var raf = window.requestAnimationFrame || window.mozRequestAnimationFrame || window.webkitRequestAnimationFrame ||
        function(fn){ return window.setTimeout(fn, 20); };
    return function(fn){ return raf(fn); };
  })();
  
  var cancelFrame = (function(){
    var cancel = window.cancelAnimationFrame || window.mozCancelAnimationFrame || window.webkitCancelAnimationFrame ||
           window.clearTimeout;
    return function(id){ return cancel(id); };
  })();
  
  function resizeListener(e){
    var win = e.target || e.srcElement;
    if (win.__resizeRAF__) cancelFrame(win.__resizeRAF__);
    win.__resizeRAF__ = requestFrame(function(){
      var trigger = win.__resizeTrigger__;
      trigger.__resizeListeners__.forEach(function(fn){
        fn.call(trigger, e);
      });
    });
  }
  
  function objectLoad(e){
    this.contentDocument.defaultView.__resizeTrigger__ = this.__resizeElement__;
    this.contentDocument.defaultView.addEventListener('resize', resizeListener);
  }
  
  window.addResizeListener = function(element, fn){
    if (!element.__resizeListeners__) {
      element.__resizeListeners__ = [];
      if (attachEvent) {
        element.__resizeTrigger__ = element;
        element.attachEvent('onresize', resizeListener);
      }
      else {
        if (getComputedStyle(element).position == 'static') element.style.position = 'relative';
        var obj = element.__resizeTrigger__ = document.createElement('object'); 
        obj.setAttribute('style', 'display: block; position: absolute; top: 0; left: 0; height: 100%; width: 100%; overflow: hidden; pointer-events: none; z-index: -1;');
        obj.__resizeElement__ = element;
        obj.onload = objectLoad;
        obj.type = 'text/html';
        if (isIE) element.appendChild(obj);
        obj.data = 'about:blank';
        if (!isIE) element.appendChild(obj);
      }
    }
    element.__resizeListeners__.push(fn);
  };
  
  window.removeResizeListener = function(element, fn){
    element.__resizeListeners__.splice(element.__resizeListeners__.indexOf(fn), 1);
    if (!element.__resizeListeners__.length) {
      if (attachEvent) element.detachEvent('onresize', resizeListener);
      else {
        element.__resizeTrigger__.contentDocument.defaultView.removeEventListener('resize', resizeListener);
        element.__resizeTrigger__ = !element.removeChild(element.__resizeTrigger__);
      }
    }
  }
}

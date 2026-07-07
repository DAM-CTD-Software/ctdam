import json
import logging
import random
import webbrowser
from pathlib import Path
from urllib.parse import quote

from bokeh.layouts import column, row
from bokeh.models import (
    Button,
    ColumnDataSource,
    CustomJS,
    Div,
    HoverTool,
    LinearAxis,
    Range1d,
    Slider,
    Title,
)
from bokeh.plotting import figure, output_file, save, show
from bokeh.resources import INLINE
from bs4 import BeautifulSoup
from tomlkit.toml_file import TOMLFile

from ctdam.conv.hexdecoder import decode_hex
from ctdam.parser import CnvFile, CTDData

logger = logging.getLogger(__name__)

bokeh_validation_logger = logging.getLogger("bokeh.core.validation.check")
if not getattr(
    bokeh_validation_logger, "_fixed_sizing_filter_installed", False
):
    bokeh_validation_logger.addFilter(
        lambda record: "W-1005 (FIXED_SIZING_MODE)" not in record.getMessage()
    )
    bokeh_validation_logger._fixed_sizing_filter_installed = True


def check_and_create_path(dir: Path | str):
    """
    Create given directory path if not found.

    Parameters
    ----------
    dir: Path | str
        Path to target directory
    """
    dir = Path(dir)
    if dir == Path("."):
        return

    if not dir.exists():
        dir.mkdir(parents=True)


def cruise_plots(
    directory: Path | str = "",
    output_directory: Path | str = "html",
    output_name: str = "main.html",
    embed_contents: bool = False,
    html_title: str = "",
    overwrite: bool = False,
    no_new_plots: bool = False,
    size_limit: int = 10,
    filter: str = "",
    show_html: bool = True,
    config_path: Path | str = "vis_config.toml",
    file_type: str = "cnv",
) -> Path | None:
    """
    Run basic_bokeh_plot and create_main_html and handle inputs.

    Parameters
    ----------
    directory: Path | str
        The directory to look for data files to plot (Default value = "")
    output_directory: Path | str
        The directory to save .html file to (Default value = "html")
    output_name: str
        The name of the main html file (Default value = "main.html")
    embed_contents: bool
        Whether to embed plot htmls into main html (Default value = False)
    html_title: str
        The header of the main html (Default value = "")
    overwrite: bool
        Whether to overwrite an existing main html (Default value = False)
    no_new_plots: bool
        Whether to not overwrite existing plot htmls (Default value = False)
    size_limit: int
        Data file size limit in MB (Default value = 10)
    filter: str
        A search filter for files (Default value = "")
    show_html: bool
        Whether to open main html in browser (Default value = True)
    config_path: Path | str
        The path to vis configuration info (Default value = "vis_config.toml")
    file_type: str
        The file type to search for (Default value = "cnv")

    Returns
    -------
    The path to the main html.
    """
    if not no_new_plots:
        output_directory = (
            Path(output_directory)
            if str(output_directory)
            else Path(directory)
        )
        if not output_directory.exists():
            output_directory.mkdir()
        if not file_type:
            file_type = ".cnv"

        file_type = f".{file_type}" if not file_type[0] == "." else file_type
        file_filter = f"*{filter}*" if filter else "*"

        for file in Path(directory).glob(f"{file_filter}{file_type}"):
            if file.stat().st_size > size_limit * 1000000:
                logger.info(f"{file} above size limit of {size_limit}MB")
                continue
            if (
                Path(output_directory)
                .joinpath(file.name)
                .with_suffix(".html")
                .exists()
            ) and not overwrite:
                continue
            try:
                basic_bokeh_plot(
                    ctd_data=str(file),
                    output_directory=output_directory,
                    print_plot=True,
                    metadata=True,
                    show_plot=False,
                    config_path=config_path,
                )
            except Exception as error:
                import traceback

                logger.warning(f"Could not create a plot for {file}: {error}")
                traceback.print_exc()
                continue

    if output_directory:
        directory = output_directory

    output_path = create_main_html(
        directory_path=directory,
        output_name=output_name,
        output_directory=output_directory,
        embed_contents=embed_contents,
        title=html_title,
        show_html=show_html,
    )
    return output_path


def basic_bokeh_plot(
    ctd_data: CTDData | CnvFile | Path | str,
    print_plot: bool = False,
    output_name: str = "",
    output_directory: Path | str = "",
    metadata: bool = True,
    show_plot: bool = True,
    y_axis_params: list[str] = ["prDM", "depSM"],
    config_path: Path | str = "vis_config.toml",
):
    """
    Create a .html plot for a CTD cast.

    Parameters
    ----------
    ctd_data: CTDData | CnvFile | Path | str
        The data to operate on
    print_plot: bool
        Whether to save the plot to disk (Default value = False)
    output_name: str
        The name of the output file (Default value = "")
    output_directory: Path | str
        The directory to store the output file in (Default value = "")
    metadata: bool
        Whether to save metadata in the file (Default value = True)
    show_plot: bool
        Whether to open the plot in a browser (Default value = True)
    y_axis_params: list[str] :
        Possible parameters for the y axis
    config_path: Path | str
        The path to the config file (Default value = "vis_config.toml")
    """
    if isinstance(ctd_data, Path | str):
        suffix = Path(ctd_data).suffix
        if suffix == ".cnv":
            ctd_data = CnvFile(ctd_data).to_ctd_data()
        elif suffix == ".hex":
            ctd_data = decode_hex(ctd_data)

    try:
        file_path = ctd_data.metadata_source.path_to_file
    except AttributeError:
        file_path = ctd_data.path_to_file

    source = ColumnDataSource(ctd_data.parameters.get_pandas_dataframe())

    try:
        config = TOMLFile(config_path).read()
    except Exception:
        try:
            config = TOMLFile(
                Path(__file__).parent.joinpath(config_path)
            ).read()
        except Exception:
            config = {}

    y_axis_param = ""
    y_axis_label = ""
    for param in y_axis_params:
        for p in ctd_data.parameters.get_parameter_list():
            if param == p.name:
                y_axis_param = param
                y_axis_label = p.metadata["longinfo"]
                break

    if not y_axis_param:
        logger.info(
            f"Could not find any of {y_axis_params} inside {file_path}"
        )
        return

    fig = figure(
        y_axis_label=y_axis_label,
        sizing_mode="stretch_both",
        tools="pan, box_zoom, wheel_zoom, xwheel_zoom, ywheel_zoom, reset, save",
        active_drag="pan",
        active_scroll="wheel_zoom",
    )
    fig.xaxis.visible = False
    non_plotting = [
        "flag",
        "dz/dtM",
        "timeS",
        "scan",
        "nbf",
        "nbin",
        "latitude",
        "longitude",
        "altM",
    ] + y_axis_params

    parameters = [
        param
        for param in ctd_data.parameters.get_parameter_list()
        if param.name not in non_plotting
    ]

    fig.extra_x_ranges = {
        param.name: Range1d(start=0, end=param.span[1]) for param in parameters
    }

    fig.y_range = Range1d(
        start=ctd_data.parameters[y_axis_param].span[1],
        end=ctd_data.parameters[y_axis_param].span[0],
    )

    colors = [
        f"#{random.randint(0, 0xFFFFFF):06x}" for _ in range(len(parameters))
    ]

    # ── Print button ──────────────────────────────────────────────────────────
    print_button = Button(label="Print", width=80, button_type="default")

    if metadata:
        title = Title(
            text=" | ".join(
                [f"{k} = {v}" for k, v in ctd_data.metadata.items()]
            ),
            text_font_size="8pt",
            align="left",
            text_color="black",
        )
        fig.add_layout(title, "above")
        proc_meta = Title(
            text="".join(ctd_data.processing_steps._form_processing_info()),
            text_font_size="0pt",
            align="center",
            text_color="gray",
        )
        fig.add_layout(proc_meta, "below")

    sliders = []

    for index, parameter in enumerate(parameters):
        color = colors[index]
        name = parameter.name
        param_type = parameter.param.lower()
        unit = parameter.unit
        label = f"{name} [{unit}]"
        show_param = None

        def _use_config_data(info_dict):
            """


            Parameters
            ----------
            info_dict


            Returns
            -------

            """
            sensor = parameter.sensor_number - 1
            try:
                color = info_dict["colors"][sensor]
            except KeyError:
                color = colors[index]
            try:
                fig.extra_x_ranges[name] = Range1d(
                    start=info_dict["span_start"],
                    end=info_dict["span_end"],
                )
            except KeyError:
                pass
            try:
                show_param = bool(info_dict["show"])
            except KeyError:
                show_param = None
            return color, show_param

        if config:
            matches = [key for key in config if param_type.startswith(key)]
            for match in matches:
                for unit_desc in config[match]:
                    if (
                        unit_desc.replace("-", " ").replace("_", "/")
                        in unit.lower()
                    ):
                        color, show_param = _use_config_data(
                            config[match][unit_desc]
                        )
                        break
                    elif unit_desc in [
                        "show",
                        "colors",
                        "span_start",
                        "span_end",
                    ]:
                        color, show_param = _use_config_data(config[match])
                        break

        xaxis = LinearAxis(
            x_range_name=name,
            axis_label_text_color=color,
            major_label_text_color=color,
            major_tick_line_color=color,
            axis_line_color=color,
        )

        line = fig.line(
            name,
            y_axis_param,
            source=source,
            line_width=2,
            legend_label=label,
            color=color,
            x_range_name=name,
        )
        fig.add_layout(xaxis, "below")

        # ── X-axis slider ─────────────────────────────────────────────────────
        x_range = fig.extra_x_ranges[name]
        max_delta = x_range.end

        slider = Slider(
            title=f"{label} End ±",
            start=-max_delta,
            end=+max_delta,
            value=0,
            step=max_delta / 200 if max_delta else 1,
            sizing_mode="stretch_width",
        )
        slider.js_on_change(
            "value",
            CustomJS(
                args=dict(x_range=x_range),
                code="""
                if (x_range.base_val === undefined) {
                    x_range.base_val = x_range.end;
                }
                const new_end = x_range.base_val + cb_obj.value;
                x_range.end = new_end > x_range.start ? new_end : x_range.start + 0.001;
                """,
            ),
        )

        fig.add_tools(
            HoverTool(
                renderers=[line],
                tooltips=[
                    ("Name", label),
                    (
                        "Color",
                        '<span class="bk-tooltip-color-block" '
                        'style="background-color:{}"> </span>'.format(color),
                    ),
                    (f"{unit}", "$x"),
                    ("db", "$y"),
                ],
            )
        )

        xaxis.visible = line.visible = _auto_show_plot(name, unit, show_param)
        slider.visible = line.visible
        x_range.name = f"axis-range::{name}"
        slider.name = f"axis-slider::{name}"

        # Sync axis + slider visibility with legend toggle
        line.js_on_change(
            "visible",
            CustomJS(
                args=dict(xaxis=xaxis, slider=slider, line=line),
                code="""
                xaxis.visible  = line.visible;
                slider.visible = line.visible;
                """,
            ),
        )
        sliders.append(slider)

    fig.legend.location = "top_left"
    fig.legend.click_policy = "hide"
    fig.legend.background_fill_alpha = 0.1
    fig.legend.background_fill_color = None

    # ── Sidebar: sliders + buttons ────────────────────────────────────────────
    slider_column = column(
        *sliders,
        sizing_mode="fixed",
        width=220,
        css_classes=["bokeh-slider-sidebar"],
    )

    base_starts = [
        fig.extra_x_ranges[param.name].start for param in parameters
    ]
    base_ends = [fig.extra_x_ranges[param.name].end for param in parameters]
    range_args = {
        param.name: fig.extra_x_ranges[param.name] for param in parameters
    }
    param_labels = [f"{param.name} [{param.unit}]" for param in parameters]
    param_names = [param.name for param in parameters]
    plot_storage_key = f"ctd_axis_config::{file_path.stem}"
    global_storage_key = "ctd_axis_config_global"

    # ── Settings modal button ─────────────────────────────────────────────────
    settings_button = Button(
        label="⚙",
        width=36,
        button_type="default",
        css_classes=["bk-settings-btn"],
    )
    settings_button.js_on_click(
        CustomJS(
            args=dict(
                x_ranges=range_args,
                param_names=param_names,
                param_labels=param_labels,
                sliders=sliders,
                base_starts=base_starts,
                base_ends=base_ends,
                plot_storage_key=plot_storage_key,
                global_storage_key=global_storage_key,
            ),
            code="""
        const existing = document.getElementById('_span_settings_modal');
        if (existing) { existing.remove(); return; }

        const storage = (window.parent && window.parent.localStorage)
            ? window.parent.localStorage
            : window.localStorage;

        function collectConfig() {
            const config = {};
            param_names.forEach(function(name, i) {
                const xr = x_ranges[name];
                const s = parseFloat(inputs[name]['start'].value);
                const e = parseFloat(inputs[name]['end'].value);
                if (!isNaN(s)) xr.start = s;
                if (!isNaN(e)) {
                    xr.end = e;
                    xr.base_val = e;
                    const sld = sliders[i];
                    if (sld) {
                        sld.value = 0;
                        sld.start = -e;
                        sld.end = e;
                        sld.step = (e * 2) / 200;
                    }
                }
                config[name] = { start: xr.start, end: xr.end };
            });
            return config;
        }

        function applyConfig(config) {
            param_names.forEach(function(name, i) {
                const xr = x_ranges[name];
                const fallback = {
                    start: base_starts[i],
                    end: base_ends[i],
                };
                const next = (config && config[name]) ? config[name] : fallback;

                xr.start = next.start;
                xr.end = next.end;
                xr.base_val = next.end;

                const sld = sliders[i];
                if (sld) {
                    sld.value = 0;
                    sld.start = -next.end;
                    sld.end = next.end;
                    sld.step = next.end ? (next.end * 2) / 200 : 1;
                }

                if (inputs[name]) {
                    inputs[name].start.value = next.start.toFixed(2);
                    inputs[name].end.value = next.end.toFixed(2);
                }
            });
        }

        const overlay = document.createElement('div');
        overlay.id = '_span_settings_modal';
        overlay.style.cssText = 'position:fixed;top:0;left:0;width:100%;height:100%;background:rgba(0,0,0,0.45);z-index:9999;display:flex;align-items:center;justify-content:center;';

        const modal = document.createElement('div');
        modal.style.cssText = 'background:#fff;border-radius:6px;padding:24px 28px;min-width:360px;max-width:520px;width:90%;box-shadow:0 8px 32px rgba(0,0,0,0.22);font-family:IBM Plex Mono,monospace;font-size:13px;max-height:80vh;overflow-y:auto;';

        const title = document.createElement('div');
        title.textContent = 'X-Axis Span Settings';
        title.style.cssText = 'font-weight:600;font-size:14px;margin-bottom:18px;letter-spacing:0.04em;color:#1a1a1a;border-bottom:1px solid #eee;padding-bottom:10px;';
        modal.appendChild(title);

        const inputs = {};
        param_names.forEach(function(name, i) {
            const rowEl = document.createElement('div');
            rowEl.style.cssText = 'display:flex;align-items:center;gap:10px;margin-bottom:12px;';
            const lbl = document.createElement('span');
            lbl.textContent = param_labels[i];
            lbl.style.cssText = 'flex:1;color:#444;font-size:11px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis;min-width:0;';
            rowEl.appendChild(lbl);

            ['start','end'].forEach(function(which) {
                const wrapper = document.createElement('div');
                wrapper.style.cssText = 'display:flex;flex-direction:column;align-items:center;gap:2px;';
                const sublbl = document.createElement('span');
                sublbl.textContent = which === 'start' ? 'Start' : 'End';
                sublbl.style.cssText = 'font-size:9px;color:#aaa;text-transform:uppercase;letter-spacing:0.1em;';
                wrapper.appendChild(sublbl);
                const inp = document.createElement('input');
                inp.type = 'number';
                const val = which === 'start' ? x_ranges[name].start : x_ranges[name].end;
                inp.value = val.toFixed(2);
                inp.style.cssText = 'width:80px;padding:5px 7px;border:1px solid #ccc;border-radius:3px;font-family:IBM Plex Mono,monospace;font-size:12px;color:#1a1a1a;background:#f8f8f8;';
                inp.addEventListener('focus', function() { inp.style.borderColor='#1a1a1a'; });
                inp.addEventListener('blur',  function() { inp.style.borderColor='#ccc'; });
                if (!inputs[name]) inputs[name] = {};
                inputs[name][which] = inp;
                wrapper.appendChild(inp);
                rowEl.appendChild(wrapper);
            });
            modal.appendChild(rowEl);
        });

        const btnRow = document.createElement('div');
        btnRow.style.cssText = 'display:flex;justify-content:flex-end;gap:10px;margin-top:20px;padding-top:14px;border-top:1px solid #eee;';

        function attachHoverAnimation(button, normalStyle, hoverStyle) {
            button.style.cssText = normalStyle;
            button.addEventListener('mouseenter', function() {
                button.style.cssText = hoverStyle;
            });
            button.addEventListener('mouseleave', function() {
                button.style.cssText = normalStyle;
            });
        }
        const applyBtn = document.createElement('button');
        applyBtn.textContent = 'Apply';
        attachHoverAnimation(
            applyBtn,
            'padding:7px 18px;border:1px solid #ccc;border-radius:3px;background:#f5f5f5;font-family:IBM Plex Mono,monospace;font-size:12px;cursor:pointer;',
            'padding:7px 18px;border:1px solid #ccc;border-radius:3px;background:#e0e0e0;font-family:IBM Plex Mono,monospace;font-size:12px;cursor:pointer;'
        );
        applyBtn.onclick = function() {
            const plotConfig = collectConfig();
            storage.setItem(plot_storage_key, JSON.stringify(plotConfig));
            overlay.remove();
        };

        const applyAllBtn = document.createElement('button');
        applyAllBtn.textContent = 'Apply to all Plots';
        attachHoverAnimation(
            applyAllBtn,
            'padding:7px 18px;border:1px solid #ccc;border-radius:3px;background:#f5f5f5;font-family:IBM Plex Mono,monospace;font-size:12px;cursor:pointer;',
            'padding:7px 18px;border:1px solid #ccc;border-radius:3px;background:#e0e0e0;font-family:IBM Plex Mono,monospace;font-size:12px;cursor:pointer;'
        );
        applyAllBtn.onclick = function() {
            const globalConfig = collectConfig();
            Object.keys(storage).forEach(function(key) {
                if (key.startsWith('ctd_axis_config::')) {
                    storage.removeItem(key);
                }
            });
            storage.setItem(global_storage_key, JSON.stringify(globalConfig));
            overlay.remove();
        };

        const resetPlotBtn = document.createElement('button');
        resetPlotBtn.textContent = 'Reset This Plot';
        attachHoverAnimation(
            resetPlotBtn,
                'padding:7px 18px;border:1px solid #ccc;border-radius:3px;background:#f5f5f5;font-family:IBM Plex Mono,monospace;font-size:12px;cursor:pointer;',
                'padding:7px 18px;border:1px solid #ccc;border-radius:3px;background:#e0e0e0;font-family:IBM Plex Mono,monospace;font-size:12px;cursor:pointer;'
        );
        resetPlotBtn.onclick = function() {
            const plotDefaults = {};
            param_names.forEach(function(name, i) {
                plotDefaults[name] = {
                    start: base_starts[i],
                    end: base_ends[i],
                };
            });
            storage.setItem(plot_storage_key, JSON.stringify(plotDefaults));
            applyConfig(plotDefaults);
            overlay.remove();
        };

        const resetGlobalBtn = document.createElement('button');
        resetGlobalBtn.textContent = 'Reset Global Settings';
        attachHoverAnimation(
            resetGlobalBtn,
            'padding:7px 18px;border:1px solid #ccc;border-radius:3px;background:#f5f5f5;font-family:IBM Plex Mono,monospace;font-size:12px;cursor:pointer;',
            'padding:7px 18px;border:1px solid #ccc;border-radius:3px;background:#e0e0e0;font-family:IBM Plex Mono,monospace;font-size:12px;cursor:pointer;'
        );
        resetGlobalBtn.onclick = function() {
            storage.removeItem(global_storage_key);
            const localConfig = JSON.parse(storage.getItem(plot_storage_key) || 'null');
            applyConfig(localConfig);
            overlay.remove();
        };

        const cancelBtn = document.createElement('button');
        cancelBtn.textContent = 'Cancel';
        attachHoverAnimation(
            cancelBtn,
            'padding:7px 18px;border:1px solid #ccc;border-radius:3px;background:#f5f5f5;font-family:IBM Plex Mono,monospace;font-size:12px;cursor:pointer;',
            'padding:7px 18px;border:1px solid #ccc;border-radius:3px;background:#e0e0e0;font-family:IBM Plex Mono,monospace;font-size:12px;cursor:pointer;'
        );
        cancelBtn.onclick = () => overlay.remove();

        btnRow.appendChild(cancelBtn);
    btnRow.appendChild(resetPlotBtn);
        btnRow.appendChild(resetGlobalBtn);
        btnRow.appendChild(applyAllBtn);
        btnRow.appendChild(applyBtn);
        modal.appendChild(btnRow);
        overlay.appendChild(modal);
        document.body.appendChild(overlay);
        """,
        )
    )

    # ── Sidebar toggle button ─────────────────────────────────────────────────
    toggle_button = Button(
        label="◀ Adjustment",
        width=100,
        button_type="default",
    )
    toggle_button.js_on_click(
        CustomJS(
            args=dict(
                slider_col=slider_column,
                btn=toggle_button,
                bsn=settings_button,
                bpr=print_button,
            ),
            code="""
        if (slider_col.visible) {
            slider_col.visible = false;
            bsn.visible = false;
            bpr.visible = false;
            btn.label = "▶";
            btn.width = 30;
        } else {
            slider_col.visible = true;
            bsn.visible = true;
            bpr.visible = true;
            btn.label = "◀ Adjustment";
            btn.width = 100;
        }
        """,
        )
    )

    btn_row = row(
        toggle_button, settings_button, print_button, sizing_mode="fixed"
    )
    control_sidebar = column(btn_row, slider_column, sizing_mode="fixed")
    control_sidebar.css_classes = ["plot-control-sidebar"]
    plot_layout = row(
        control_sidebar,
        fig,
        sizing_mode="stretch_both",
    )
    plot_layout.css_classes = ["plot-wrapper"]
    print_button.js_on_click(
        CustomJS(
            args=dict(sidebar=control_sidebar),
            code="""
        const previousVisibility = sidebar.visible;
        sidebar.visible = false;

        const restoreSidebar = () => {
            sidebar.visible = previousVisibility;
            window.dispatchEvent(new Event('resize'));
            window.removeEventListener('afterprint', restoreSidebar);
        };

        window.addEventListener('afterprint', restoreSidebar);
        setTimeout(() => {
            window.print();
            setTimeout(restoreSidebar, 250);
        }, 100);
    """,
        )
    )

    if print_plot:
        output_name = file_path.stem if not output_name else str(output_name)
        output_directory = (
            Path(output_directory).absolute()
            if output_directory
            else file_path.parent.absolute()
        )
        check_and_create_path(output_directory)
        html_path = output_directory.joinpath(output_name).with_suffix(".html")
        output_file(
            html_path, title=f"Plot of {file_path.name}", mode="inline"
        )
        save(plot_layout, resources=INLINE)

        # Inject custom metadata + print CSS
        custom_metadata = {
            "title": file_path.stem,
            "text": " | ".join(
                [f"{k} = {v}" for k, v in ctd_data.metadata.items()]
            ),
            "processing": "".join(
                ctd_data.processing_steps._form_processing_info()
            ),
        }
        with open(html_path, "r", encoding="utf-8") as f:
            html = f.read()

        inject = (
            '<script type="application/json" id="custom-plot-metadata">\n'
            + json.dumps(custom_metadata)
            + "\n</script>"
        )
        axis_restore_script = f"""<script>
(function() {{
    const plotStorageKey = {json.dumps(plot_storage_key)};
    const globalStorageKey = {json.dumps(global_storage_key)};
    const paramNames = {json.dumps(param_names)};

    function applyConfig(doc, config) {{
        if (!config) return;
        paramNames.forEach(function(name) {{
            if (!config[name]) return;
            const xr = doc.get_model_by_name(`axis-range::${{name}}`);
            if (!xr) return;
            xr.start = config[name].start;
            xr.end = config[name].end;
            xr.base_val = config[name].end;
            xr.change.emit();

            const slider = doc.get_model_by_name(`axis-slider::${{name}}`);
            if (slider) {{
                slider.value = 0;
                slider.start = -config[name].end;
                slider.end = config[name].end;
                slider.step = config[name].end ? (config[name].end * 2) / 200 : 1;
                slider.change.emit();
            }}
        }});
    }}

    function restoreAxisConfig() {{
        const storage = (window.parent && window.parent.localStorage)
            ? window.parent.localStorage
            : window.localStorage;
        if (!window.Bokeh || !Bokeh.documents || !Bokeh.documents.length) return false;
        const doc = Bokeh.documents[0];
        applyConfig(doc, JSON.parse(storage.getItem(globalStorageKey) || 'null'));
        applyConfig(doc, JSON.parse(storage.getItem(plotStorageKey) || 'null'));
        return true;
    }}

    function waitForBokeh(attempt) {{
        if (restoreAxisConfig() || attempt > 100) return;
        window.setTimeout(function() {{ waitForBokeh(attempt + 1); }}, 50);
    }}

    if (document.readyState !== 'loading') {{
        waitForBokeh(0);
    }} else {{
        document.addEventListener('DOMContentLoaded', function() {{
            waitForBokeh(0);
        }});
    }}
}})();
</script>"""
        print_css = """<style>
@media print {
    .plot-control-sidebar, .bokeh-slider-sidebar, .bk-settings-btn, .bk-btn, button { display: none !important; }
    .plot-wrapper { width: auto !important; height: auto !important; }
    body { margin: 0 !important; }
}
</style>"""
        # Only replace the final closing tags to avoid corrupting JS strings
        # that may legitimately contain "</head>" or "</body>".
        if "</head>" in html:
            html_head, html_tail = html.rsplit("</head>", 1)
            html = html_head + print_css + "\n</head>" + html_tail
        if "</body>" in html:
            html_body, html_tail = html.rsplit("</body>", 1)
            html = (
                html_body
                + axis_restore_script
                + "\n"
                + inject
                + "\n</body>"
                + html_tail
            )

        with open(html_path, "w", encoding="utf-8") as f:
            f.write(html)

    if show_plot:
        show(plot_layout)


def _auto_show_plot(name: str, unit: str, show_param: bool | None) -> bool:
    """
    Whether to automatically show the given parameter in the plot.


    Parameters
    ----------
    name: str
        The parameter name
    unit: str
        The unit off the parameter
    show_param: bool | None
        Fixed boolean to set output handling

    Returns
    -------
    A boolean to indicate whether to show the parameter or not.

    """
    if isinstance(show_param, bool):
        return show_param
    # Temperature
    if "deg C" in unit and not name.startswith(("pta", "potemp")):
        return True
    # Salinity
    elif "PSU" in unit:
        return True
    # Oxygen
    elif name.startswith("sb") and "%" not in unit:
        return True
    else:
        return False


def create_main_html(
    directory_path: Path | str,
    output_name: str = "main_plots.html",
    output_directory: Path | str = "",
    embed_contents: bool = True,
    title: str = "",
    show_html: bool = True,
) -> Path | None:
    """
    Assemble a main .html file that stores all individual .html plots.

    Does also allow to interactively change plotting parameters and the
    seamless selection of plots.

    Parameters
    ----------
    directory_path: Path | str
        The path to the .html plot files
    output_name: str
        The name of the main .html file (Default value = "main_plots.html")
    output_directory: Path | str
        The directory to write the main .html file to (Default value = "")
    embed_contents: bool
        Whether to embed the .html plots into the main html file (Default value = True)
    title: str
        The title of the main file (Default value = "")
    show_html: bool
        Whether to open the main .html in a browser (Default value = True)

    Returns
    -------
    The path to the main .html file.
    """
    check_and_create_path(directory_path)
    check_and_create_path(output_directory)
    html_files = [
        file
        for file in Path(directory_path).iterdir()
        if file.suffix == ".html"
    ]
    if not html_files:
        print(f"No HTML files found in {directory_path}")
        return

    dropdown_options = []
    plot_metadata = {}
    plot_html_map = {}

    for i, html_file in enumerate(sorted(html_files)):
        if html_file.name == output_name or html_file.name.startswith("."):
            continue
        plot_id = f"plot_{i}"

        with open(html_file, "r", encoding="utf-8") as f:
            raw_html = f.read()

        soup = BeautifulSoup(raw_html, "html.parser")
        metadata = {
            "title": html_file.stem,
            "text": "",
            "processing": "",
        }
        custom = soup.find("script", {"id": "custom-plot-metadata"})
        if custom and custom.string:
            try:
                data = json.loads(custom.string)
                metadata["title"] = data.get("title", metadata["title"])
                metadata["text"] = data.get("text", "")
                metadata["processing"] = data.get("processing", "")
            except Exception:
                pass

        plot_metadata[plot_id] = metadata
        plot_html_map[plot_id] = raw_html
        dropdown_options.append(
            f'<option value="{plot_id}">{metadata["title"]}</option>'
        )

    dropdown_options_html = "\n".join(dropdown_options)
    title = f"{directory_path} Plots" if not title else title
    try:
        svg_icon = Path("docs/images/ctd_rosette.svg").read_text(
            encoding="utf-8"
        )
        icon_href = f"data:image/svg+xml,{quote(svg_icon)}"
    except Exception:
        icon_href = ""
    main_html = f"""<!DOCTYPE html>
<html>
<head>
    <title>{title}</title>
    <link rel="icon" type="image/svg+xml" href="{icon_href}">
    <style>
        :root {{
            --font-sans: "Segoe UI", "Helvetica Neue", Helvetica, Arial, sans-serif;
            --font-mono: "Cascadia Mono", "Consolas", "Liberation Mono", "Courier New", monospace;
        }}

        *, *::before, *::after {{ box-sizing: border-box; margin: 0; padding: 0; }}

        body {{
            font-family: var(--font-sans);
            background: #f5f5f5;
            display: flex;
            flex-direction: column;
            height: 100vh;
            overflow: hidden;
        }}

        /* ── TOP BAR ── */
        .top-bar {{
            display: flex;
            align-items: stretch;
            height: 52px;
            background: #fafafa;
            border-bottom: 2px solid #1a1a1a;
            flex-shrink: 0;
        }}
        .logo-area {{
            display: flex;
            align-items: center;
            padding: 0 18px;
            border-right: 2px solid #1a1a1a;
            flex-shrink: 0;
        }}
        .logo-text {{
            font-family: var(--font-mono);
            font-size: 13px;
            font-weight: 600;
            letter-spacing: 0.04em;
            color: #1a1a1a;
            line-height: 1;
        }}
        .logo-sub {{
            display: block;
            font-size: 8px;
            font-family: var(--font-mono);
            font-weight: 400;
            color: #999;
            letter-spacing: 0.14em;
            text-transform: uppercase;
            margin-top: 3px;
        }}
        .file-selector {{
            display: flex;
            align-items: center;
            padding: 0 20px;
            gap: 10px;
            border-right: 1px solid #e0e0e0;
            flex-shrink: 0;
        }}
        .file-selector label {{
            font-size: 9px;
            font-family: var(--font-mono);
            font-weight: 600;
            text-transform: uppercase;
            letter-spacing: 0.12em;
            color: #999;
            white-space: nowrap;
        }}
        .styled-select {{
            appearance: none;
            -webkit-appearance: none;
            background: #f0f0f0;
            border: 1px solid #ccc;
            border-radius: 2px;
            padding: 6px 28px 6px 10px;
            font-family: var(--font-mono);
            font-size: 12px;
            color: #1a1a1a;
            min-width: 220px;
            max-width: 320px;
            cursor: pointer;
            background-image: url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' width='10' height='7' fill='none'%3E%3Cpath d='M1 1l4 4 4-4' stroke='%23666' stroke-width='1.5' stroke-linecap='round'/%3E%3C/svg%3E");
            background-repeat: no-repeat;
            background-position: right 10px center;
            transition: border-color 0.15s, box-shadow 0.15s;
        }}
        .styled-select:focus {{
            outline: none;
            border-color: #1a1a1a;
            box-shadow: 0 0 0 2px rgba(26,26,26,0.1);
        }}

        /* ── META CHIPS ── */
        .meta-chips {{
            display: flex;
            align-items: center;
            padding: 0 8px;
            flex: 1;
            overflow: hidden;
        }}
        .meta-chip {{
            display: flex;
            flex-direction: column;
            justify-content: center;
            padding: 0 16px;
            border-right: 1px solid #e8e8e8;
            height: 100%;
        }}
        .meta-chip:first-child {{ padding-left: 20px; }}
        .chip-key {{
            font-family: var(--font-mono);
            font-size: 8px;
            text-transform: uppercase;
            letter-spacing: 0.14em;
            color: #aaa;
            line-height: 1;
            margin-bottom: 3px;
        }}
        .chip-val {{
            font-family: var(--font-mono);
            font-size: 12px;
            font-weight: 600;
            color: #1a1a1a;
            line-height: 1;
            white-space: nowrap;
        }}
        .chip-val.empty {{ color: #ccc; font-weight: 400; font-style: italic; }}

        /* ── INFO PANEL TOGGLE BUTTONS ── */
        .panel-toggles {{
            display: flex;
            align-items: center;
            gap: 4px;
            padding: 0 12px;
            border-left: 1px solid #e0e0e0;
            flex-shrink: 0;
        }}
        .panel-btn {{
            display: flex;
            align-items: center;
            gap: 6px;
            padding: 5px 10px;
            background: transparent;
            border: 1px solid transparent;
            border-radius: 3px;
            font-family: var(--font-mono);
            font-size: 10px;
            font-weight: 600;
            letter-spacing: 0.08em;
            text-transform: uppercase;
            color: #999;
            cursor: pointer;
            transition: all 0.15s;
            white-space: nowrap;
        }}
        .panel-btn:hover {{ background: #f0f0f0; color: #1a1a1a; border-color: #ddd; }}
        .panel-btn.active {{ background: #1a1a1a; color: #fff; border-color: #1a1a1a; }}
        .panel-btn .btn-dot {{
            width: 6px; height: 6px;
            border-radius: 50%;
            background: currentColor;
            flex-shrink: 0;
        }}

        /* ── INFO DRAWER ── */
        .info-drawer {{
            background: #fff;
            border-bottom: 1px solid #e0e0e0;
            overflow: hidden;
            max-height: 0;
            transition: max-height 0.25s ease, padding 0.25s ease;
            flex-shrink: 0;
        }}
        .info-drawer.open {{ max-height: 180px; overflow-y: auto; }}
        .drawer-inner {{ padding: 14px 24px; display: flex; gap: 32px; }}
        .drawer-section {{ flex: 1; min-width: 0; }}
        .drawer-section-title {{
            font-family: var(--font-mono);
            font-size: 9px;
            font-weight: 600;
            text-transform: uppercase;
            letter-spacing: 0.16em;
            color: #aaa;
            border-bottom: 1px solid #e8e8e8;
            padding-bottom: 6px;
            margin-bottom: 8px;
        }}
        .drawer-text {{
            font-family: var(--font-mono);
            font-size: 11px;
            color: #444;
            line-height: 1.6;
            white-space: pre-wrap;
            word-break: break-word;
        }}

        /* ── PLOT CONTAINER ── */
        .plot-display-container {{
            flex: 1;
            position: relative;
            overflow: hidden;
        }}
        #plot_iframe {{
            position: absolute;
            top: 0; left: 0;
            width: 100%; height: 100%;
            border: none;
            display: none;
        }}

        @page {{ size: auto; margin: 0; }}
    </style>

    <script>
        const plotMetadata = {json.dumps(plot_metadata).replace("</script>", r"<\/script>")};
        const plotHtmlMap  = {json.dumps(plot_html_map).replace("</script>", r"<\/script>")};
        let activeDrawer = null;

        function updatePlot() {{
            const dropdown = document.getElementById("plot_dropdown");
            const selectedPlotId = dropdown.value;
            const iframe = document.getElementById("plot_iframe");

            if (selectedPlotId && plotHtmlMap[selectedPlotId]) {{
                iframe.srcdoc = plotHtmlMap[selectedPlotId];
                iframe.style.display = 'block';
            }} else {{
                iframe.srcdoc = '';
                iframe.style.display = 'none';
            }}

            refreshDrawer(selectedPlotId);
            refreshChips(selectedPlotId);
        }}

        function refreshChips(plotId) {{
            const meta = plotId ? plotMetadata[plotId] : null;
            const pairs = {{}};
            if (meta && meta.text) {{
                meta.text.split(' | ').forEach(part => {{
                    const idx = part.indexOf(' = ');
                    if (idx !== -1) {{
                        pairs[part.slice(0, idx).trim()] = part.slice(idx + 3).trim();
                    }}
                }});
            }}

            const mapping = {{
                'station':    ['station'],
                'latitude':   ['latitude', 'gps_lat'],
                'longitude':  ['longitude', 'gps_lon'],
                'start_time': ['start_time', 'gps_time'],
                'ship':       ['ship', 'cruise'],
                'operator':   ['operator'],
            }};

            Object.entries(mapping).forEach(([chipName, searchTerms]) => {{
                const el = document.getElementById('chip_' + chipName);
                if (!el) return;
                const found = Object.keys(pairs).find(pKey =>
                    searchTerms.some(term => pKey.toLowerCase().includes(term.toLowerCase()))
                );
                if (found) {{
                    el.textContent = pairs[found];
                    el.classList.remove('empty');
                }} else {{
                    el.textContent = '—';
                    el.classList.add('empty');
                }}
            }});
        }}

        function refreshDrawer(plotId) {{
            if (!activeDrawer) return;
            const meta = plotId ? plotMetadata[plotId] : null;
            const metaEl = document.getElementById('drawer_meta_text');
            const procEl = document.getElementById('drawer_proc_text');
            if (metaEl) metaEl.textContent = (meta && meta.text) ? meta.text.replace(/ \\| /g, '\\n') : '';
            if (procEl) procEl.textContent = (meta && meta.processing) ? meta.processing : '';
        }}

        function toggleDrawer(panel) {{
            const drawer  = document.getElementById('info_drawer');
            const btnMeta = document.getElementById('btn_meta');
            const btnProc = document.getElementById('btn_proc');

            if (activeDrawer === panel) {{
                activeDrawer = null;
                drawer.classList.remove('open');
                btnMeta.classList.remove('active');
                btnProc.classList.remove('active');
            }} else {{
                activeDrawer = panel;
                drawer.classList.add('open');
                btnMeta.classList.toggle('active', panel === 'meta');
                btnProc.classList.toggle('active', panel === 'proc');

                const metaSection = document.getElementById('drawer_meta_section');
                const procSection = document.getElementById('drawer_proc_section');
                if (metaSection) metaSection.style.display = panel === 'meta' ? 'block' : 'none';
                if (procSection) procSection.style.display = panel === 'proc' ? 'block' : 'none';

                const dropdown = document.getElementById("plot_dropdown");
                refreshDrawer(dropdown.value);
            }}
        }}
    </script>
</head>
<body>

    <div class="top-bar">
        <div class="logo-area">
            <div class="logo-text">CTD<span class="logo-sub">Visualizer</span></div>
        </div>

        <div class="file-selector">
            <label for="plot_dropdown">Cast</label>
            <select id="plot_dropdown" class="styled-select" onchange="updatePlot()" autofocus>
                <option value="">— select a cast —</option>
                {dropdown_options_html}
            </select>
        </div>

        <div class="meta-chips">
            <div class="meta-chip">
                <span class="chip-key">Station</span>
                <span class="chip-val empty" id="chip_station">—</span>
            </div>
            <div class="meta-chip">
                <span class="chip-key">Ship</span>
                <span class="chip-val empty" id="chip_ship">—</span>
            </div>
            <div class="meta-chip">
                <span class="chip-key">Operator</span>
                <span class="chip-val empty" id="chip_operator">—</span>
            </div>
            <div class="meta-chip">
                <span class="chip-key">Lat</span>
                <span class="chip-val empty" id="chip_latitude">—</span>
            </div>
            <div class="meta-chip">
                <span class="chip-key">Lon</span>
                <span class="chip-val empty" id="chip_longitude">—</span>
            </div>
            <div class="meta-chip">
                <span class="chip-key">Date / Time</span>
                <span class="chip-val empty" id="chip_start_time">—</span>
            </div>
        </div>

        <div class="panel-toggles">
            <button id="btn_meta" class="panel-btn" onclick="toggleDrawer('meta')">
                <span class="btn-dot"></span> Metadata
            </button>
            <button id="btn_proc" class="panel-btn" onclick="toggleDrawer('proc')">
                <span class="btn-dot"></span> Processing
            </button>
        </div>
    </div>

    <div id="info_drawer" class="info-drawer">
        <div class="drawer-inner">
            <div id="drawer_meta_section" class="drawer-section" style="display:none;">
                <div class="drawer-section-title">Metadata</div>
                <div id="drawer_meta_text" class="drawer-text">Select a cast to view metadata.</div>
            </div>
            <div id="drawer_proc_section" class="drawer-section" style="display:none;">
                <div class="drawer-section-title">Processing Module Info</div>
                <div id="drawer_proc_text" class="drawer-text">Select a cast to view processing info.</div>
            </div>
        </div>
    </div>

    <div class="plot-display-container">
        <iframe id="plot_iframe"></iframe>
    </div>

</body>
</html>
"""

    output_directory = (
        Path(output_directory) if output_directory else Path(directory_path)
    )
    output_path = output_directory.joinpath(output_name)
    with open(output_path, "w", encoding="utf-8") as f:
        f.write(main_html)
    if show_html:
        webbrowser.open_new_tab(f"file://{output_path.absolute()}")
    return output_path

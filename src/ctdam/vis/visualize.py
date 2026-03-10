import json
import logging
import random
import webbrowser
from pathlib import Path

from bokeh.models import (
    ColumnDataSource,
    CustomJS,
    HoverTool,
    LinearAxis,
    Range1d,
    Title,
)
from bokeh.plotting import figure, output_file, save, show
from bs4 import BeautifulSoup
from tomlkit.toml_file import TOMLFile

from ctdam.conv.hexdecoder import decode_hex
from ctdam.parser import CnvFile, CTDData

logger = logging.getLogger(__name__)


def check_and_create_path(dir: Path | str):
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

        for file in Path(directory).glob(f"*{filter}*{file_type}"):
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
                logger.warning(f"Could not create a plot for {file}: {error}")
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
    if isinstance(ctd_data, Path | str):
        suffix = Path(ctd_data).suffix
        if suffix == ".cnv":
            ctd_data = CnvFile(ctd_data)
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

    p = figure(
        y_axis_label=y_axis_label,
        sizing_mode="stretch_both",
        tools="pan, box_zoom, wheel_zoom, xwheel_zoom, ywheel_zoom, reset, save",
        active_drag="pan",
        active_scroll="wheel_zoom",
    )
    p.xaxis.visible = False
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

    p.extra_x_ranges = {
        param.name: Range1d(start=0, end=param.span[1]) for param in parameters
    }

    p.y_range = Range1d(
        start=ctd_data.parameters[y_axis_param].span[1],
        end=ctd_data.parameters[y_axis_param].span[0],
    )

    colors = [
        f"#{random.randint(0, 0xFFFFFF):06x}" for _ in range(len(parameters))
    ]

    if metadata:
        title = Title(
            text=" | ".join(
                [f"{k} = {v}" for k, v in ctd_data.metadata.items()]
            ),
            text_font_size="8pt",
            align="left",
            text_color="black",
        )
        p.add_layout(title, "above")
        proc_meta = Title(
            text="".join(ctd_data.processing_steps._form_processing_info()),
            text_font_size="0pt",
            align="center",
            text_color="gray",
        )
        p.add_layout(proc_meta, "below")

    for index, parameter in enumerate(parameters):
        color = colors[index]
        name = parameter.name
        param_type = parameter.param.lower()
        unit = parameter.unit
        label = f"{name} [{unit}]"
        show_param = None

        def _use_config_data(info_dict):
            sensor = parameter.sensor_number - 1
            try:
                color = info_dict["colors"][sensor]
            except KeyError:
                color = colors[index]
            try:
                p.extra_x_ranges[name] = Range1d(
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
            matches = [p for p in config if param_type.startswith(p)]
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

        line = p.line(
            name,
            y_axis_param,
            source=source,
            line_width=2,
            legend_label=label,
            color=color,
            x_range_name=name,
        )
        p.add_layout(xaxis, "below")

        p.add_tools(
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

        # JavaScript callback to hide/show the x-axis when the line is hidden/shown
        callback = CustomJS(
            args=dict(xaxis=xaxis, line=line),
            code="""
            xaxis.visible = line.visible;
        """,
        )
        line.js_on_change("visible", callback)

    p.legend.location = "top_left"
    p.legend.click_policy = "hide"
    p.legend.background_fill_alpha = 0.1
    p.legend.background_fill_color = None

    if print_plot:
        output_name = file_path.stem if not output_name else str(output_name)
        output_directory = (
            Path(output_directory).absolute()
            if output_directory
            else file_path.parent.absolute()
        )
        check_and_create_path(output_directory)
        output_file(
            output_directory.joinpath(output_name).with_suffix(".html"),
            title=f"Plot of {file_path.name}",
        )
        save(p)

    if show_plot:
        show(p)


def _auto_show_plot(name: str, unit: str, show_param: bool | None) -> bool:
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
    plot_iframes = []
    plot_metadata = {}

    for i, html_file in enumerate(sorted(html_files)):
        if html_file.name == output_name or html_file.name.startswith("."):
            continue
        plot_id = f"plot_{i}"

        # extract metadata from the Bokeh JSON data in the HTML file
        with open(html_file, "r", encoding="utf-8") as f:
            soup = BeautifulSoup(f.read(), "html.parser")
            script_tags = soup.find_all("script", {"type": "application/json"})

            metadata = {"title": html_file.stem, "text": ""}
            for script in script_tags:
                try:
                    # custom metadata header
                    data = json.loads(script.string)
                    html_metadata = data[list(data.keys())[0]]["roots"][0][
                        "attributes"
                    ]["above"][0]["attributes"]["text"]
                    metadata["text"] = "\n".join(html_metadata.split(" | "))
                except (json.JSONDecodeError, KeyError, TypeError):
                    pass
                try:
                    # ctdam.proc module info
                    data = json.loads(script.string)
                    html_metadata = data[list(data.keys())[0]]["roots"][0][
                        "attributes"
                    ]["below"][1]["attributes"]["text"]
                    metadata["ctdam.proc"] = "".join(html_metadata)
                except Exception:
                    pass

        plot_metadata[plot_id] = metadata
        dropdown_options.append(
            f'<option value="{plot_id}">{metadata["title"]}</option>'
        )
        if embed_contents:
            with open(html_file, "r", encoding="utf-8") as f:
                html_content = f.read()
            plot_iframes.append(
                f'<div id="{plot_id}_content" style="display: none;">{html_content}</div>'
            )
        else:
            plot_iframes.append(
                f'<iframe id="{plot_id}_content" src="{Path(html_file).absolute()}" style="display: none; border: none;"></iframe>'
            )

    dropdown_options_html = "\n".join(dropdown_options)
    plot_iframes_html = "\n".join(plot_iframes)
    title = f"{directory_path} Plots" if not title else title

    main_html = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <title>{title}</title>
        <style>
            body {{
                font-family: Arial, sans-serif;
                margin: 0;
                padding: 0;
                display: flex;
                flex-direction: column;
                height: 100vh;
            }}
            h1 {{
                text-align: center;
                background-color: #f0f0f0;
                padding: 10px;
                margin: 0;
            }}
            .container {{
                display: flex;
                flex: 1;
                overflow: hidden;
            }}
            .sidebar {{
                width: 250px;
                padding: 10px;
                background-color: #f9f9f9;
                border-right: 1px solid #ddd;
                overflow-y: auto;
            }}
            .plot-display-container {{
                flex: 1;
                padding: 10px;
                overflow-y: auto;
                position: relative;
                height: calc(100vh - 100px);
            }}
            .plot-content, .plot-iframe {{
                position: absolute;
                top: 0;
                left: 0;
                width: 100%;
                // height: 100%;
                height: calc(100vh - 180px);
                border: none;
            }}
            .metadata {{
                margin-top: 20px;
                padding: 10px;
                background-color: #f0f0f0;
                border-radius: 5px;
                white-space: pre-wrap;
            }}
            select {{
                width: 100%;
                padding: 8px;
                margin-bottom: 10px;
            }}
            .proc_meta {{
                font-size: 12px;
            }}

            @media print {{
                body {{
                    visibility: hidden;
                    overflow: visible !important;
                }}
                .sidebar {{
                    display: none;
                }}
                .container {{
                    visibility: visible;
                    position: absolute;
                    top: 0;
                    left: 0;
                    height: 100vh;
                    width: 100vw;
                    overflow: visible !important;
                }}
            }}
            @page {{
                size: auto;
                margin: 0;
            }}
        </style>
        <script>
            // Embed the metadata as a JavaScript object
            const plotMetadata = {json.dumps(plot_metadata)};

            function updatePlot() {{
                const dropdown = document.getElementById("plot_dropdown");
                const selectedPlotId = dropdown.value;
                const plotDisplayContainer = document.querySelector('.plot-display-container');

                // Hide all plots
                document.querySelectorAll('[id$="_content"]').forEach(plot => {{
                    plot.style.display = "none";
                }});

                // Show the selected plot
                const selectedPlot = document.getElementById(selectedPlotId + "_content");
                if (selectedPlot) {{
                    selectedPlot.style.display = "block";
                    selectedPlot.style.position = "absolute";
                    selectedPlot.style.top = "0";
                    selectedPlot.style.left = "0";
                    selectedPlot.style.width = "100%";
                    selectedPlot.style.height = "100%";
                }}

                // Update metadata
                const metadataDiv = document.getElementById("metadata");
                if (selectedPlotId) {{
                    const selectedMetadata = plotMetadata["{'" + selectedPlotId + "'}"];

                    metadataDiv.innerHTML = `<h3>Metadata</h3><p>${{selectedMetadata.text}}</p><h4>Processing Module Info</h4><p id="proc_meta" class="proc_meta">${{selectedMetadata.ctdam.proc}}</p>`;
                }} else {{
                    metadataDiv.innerHTML = `<p>Select a plot to view metadata.</p>`;
                }}
            }}

            function printSelectedPlot() {{
                const selectedPlotId = document.getElementById('plot_dropdown').value;
                if (!selectedPlotId) {{
                    alert('Please select a plot to print.');
                    return;
                }}

                const selectedPlot = document.getElementById(selectedPlotId + "_content");
                if (selectedPlot) {{
                    selectedPlot.style.display = "block";
                }}

                window.print();
        }}
        </script>
    </head>
    <body>
        <h1>{title}</h1>
        <div class="container">
            <div class="sidebar">
                <label for="plot_dropdown">Select Plot:</label>
                <select id="plot_dropdown" onchange="updatePlot()" multiple=True size=5 autofocus=True>
                    {dropdown_options_html}
                </select>
                <button id="print-button" onclick="printSelectedPlot()">Print</button>
                <div id="metadata" class="metadata">
                    <p>Select a plot to view metadata.</p>
                </div>
            </div>
            <div class="plot-display-container">
                {plot_iframes_html}
            </div>
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

args <- commandArgs(trailingOnly = TRUE)

csv_path <- if (length(args) >= 1) args[[1]] else "results/benchmark_results.csv"
output_dir <- if (length(args) >= 2) args[[2]] else "results/plots"

dir.create(output_dir, recursive = TRUE, showWarnings = FALSE)

rows <- read.csv(csv_path, stringsAsFactors = FALSE)

if (nrow(rows) == 0) {
  stop("Benchmark CSV is empty.")
}

rows <- rows[tolower(rows$policy) %in% c("lru", "clock"), ]

if (nrow(rows) == 0) {
  stop("Benchmark CSV does not contain LRU or Clock rows.")
}

rows$policy <- tolower(rows$policy)
rows$workload_type <- tolower(rows$workload_type)
rows$page_capacity <- as.integer(rows$page_capacity)
rows$pool_size <- as.integer(rows$pool_size)

metric_specs <- list(
  list(key = "hit_rate", label = "Hit Rate"),
  list(key = "simulated_time_ms", label = "Simulated Time (ms)"),
  list(key = "disk_reads", label = "Disk Reads"),
  list(key = "evictions", label = "Evictions")
)

policy_colors <- c(lru = "#1f77b4", clock = "#d62728")
page_capacities <- sort(unique(rows$page_capacity))
line_styles <- seq_along(page_capacities)
names(line_styles) <- as.character(page_capacities)
workloads <- sort(unique(rows$workload_type))
pool_sizes <- sort(unique(rows$pool_size))

plot_metric <- function(metric_key, metric_label, output_path) {
  values <- rows[[metric_key]]
  value_range <- range(values, na.rm = TRUE)
  if (value_range[1] == value_range[2]) {
    padding <- if (value_range[1] == 0) 1 else abs(value_range[1]) * 0.1
  } else {
    padding <- (value_range[2] - value_range[1]) * 0.08
  }
  ylim <- c(value_range[1] - padding, value_range[2] + padding)

  png(filename = output_path, width = 1400, height = 900, res = 150)
  par(mfrow = c(3, 2), mar = c(4, 4, 3, 1), oma = c(0, 0, 4, 0))

  for (workload in workloads) {
    workload_rows <- rows[rows$workload_type == workload, ]
    plot(
      x = NA,
      y = NA,
      xlim = range(pool_sizes),
      ylim = ylim,
      xaxt = "n",
      xlab = "Buffer Pool Size",
      ylab = metric_label,
      main = paste(toupper(substr(workload, 1, 1)), substring(workload, 2), sep = "")
    )
    axis(1, at = pool_sizes)
    grid(col = "#dddddd", lty = "dotted")

    for (policy in c("lru", "clock")) {
      for (page_capacity in page_capacities) {
        series <- workload_rows[
          workload_rows$policy == policy &
            workload_rows$page_capacity == page_capacity,
        ]
        if (nrow(series) == 0) {
          next
        }
        series <- series[order(series$pool_size), ]
        lines(
          x = series$pool_size,
          y = series[[metric_key]],
          type = "o",
          col = policy_colors[[policy]],
          lty = line_styles[[as.character(page_capacity)]],
          lwd = 2,
          pch = 16
        )
      }
    }
  }

  plot.new()
  legend(
    "center",
    legend = c("LRU", "Clock"),
    col = policy_colors[c("lru", "clock")],
    lty = 1,
    lwd = 2,
    pch = 16,
    bty = "n",
    cex = 1.1,
    title = "Policy"
  )
  legend(
    "bottom",
    legend = paste("Page Capacity", page_capacities),
    col = "black",
    lty = line_styles,
    lwd = 2,
    bty = "n",
    cex = 1.0,
    title = "Line Style"
  )

  mtext(paste("DB Simulator", metric_label), outer = TRUE, cex = 1.3, line = 1)
  dev.off()
}

saved_paths <- character()
for (spec in metric_specs) {
  output_path <- file.path(output_dir, paste0(spec$key, ".png"))
  plot_metric(spec$key, spec$label, output_path)
  saved_paths <- c(saved_paths, output_path)
}

cat(sprintf("Saved %d plot(s):\n", length(saved_paths)))
for (path in saved_paths) {
  cat(path, "\n")
}

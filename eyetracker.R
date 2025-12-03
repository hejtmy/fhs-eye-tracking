#' Load eye-tracking data from CSV
#' @param filepath Path to CSV file
#' @param x_col Name of x-coordinate column
#' @param y_col Name of y-coordinate column
#' @param time_col Name of timestamp column
#' @param pupil_col Name of pupil size column (optional)
#' @return Data frame with standardized column names
load_eyetracking_data <- function(filepath, 
                                   x_col = "x", 
                                   y_col = "y", 
                                   time_col = "timestamp",
                                   pupil_col = NULL) {
  data <- read.csv(filepath, stringsAsFactors = FALSE)
  # Standardize column names
  result <- data.frame(
    x = data[[x_col]],
    y = data[[y_col]],
    timestamp = data[[time_col]]
  )
  if (!is.null(pupil_col) && pupil_col %in% names(data)) {
    result$pupil <- data[[pupil_col]]
  }
  # Add sample index
  result$sample_idx <- seq_len(nrow(result))
  return(result)
}

#' Convert pixel coordinates to degrees of visual angle
#' @param pixels Distance in pixels
#' @param screen_distance Distance from eye to screen (cm)
#' @param screen_width Screen width (cm)
#' @param screen_resolution_x Screen resolution in pixels (horizontal)
#' @return Distance in degrees of visual angle
pixels_to_degrees <- function(pixels, screen_distance, screen_width, screen_resolution_x) {
  distance_cm <- pixels * (screen_width / screen_resolution_x)
  degrees <- 2 * atan(distance_cm / (2 * screen_distance)) * (180 / pi)
  return(degrees)
}

#' Calculate Euclidean distance between consecutive samples
#' @param x Vector of x-coordinates
#' @param y Vector of y-coordinates
#' @return Vector of distances (length = n-1)
calculate_distances <- function(x, y) {
  n <- length(x)
  if (n < 2) return(numeric(0))

  dx <- diff(x)
  dy <- diff(y)

  distances <- sqrt(dx^2 + dy^2)
  return(distances)
}

#' Calculate point-to-point velocity
#' @param x Vector of x-coordinates
#' @param y Vector of y-coordinates  
#' @param timestamps Vector of timestamps (ms)
#' @return Vector of velocities (pixels/ms or degrees/s depending on input)
calculate_velocity <- function(x, y, timestamps) {
  n <- length(x)
  if (n < 2) return(numeric(0))
  distances <- calculate_distances(x, y)
  time_diffs <- diff(timestamps)
  time_diffs[time_diffs == 0] <- NA
  velocities <- distances / time_diffs
  return(velocities)
}

#' Smooth velocity using moving average
#' @param velocity Vector of velocities
#' @param window_size Window size for smoothing (odd number)
#' @return Smoothed velocity vector
smooth_velocity <- function(velocity, window_size = 5) {
  n <- length(velocity)
  if (n < window_size) return(velocity)
  if (window_size %% 2 == 0) window_size <- window_size + 1
  half_window <- floor(window_size / 2)
  smoothed <- rep(NA, n)
  for (i in seq_len(n)) {
    start_idx <- max(1, i - half_window)
    end_idx <- min(n, i + half_window)
    smoothed[i] <- mean(velocity[start_idx:end_idx], na.rm = TRUE)
  }
  return(smoothed)
}

#' Detect fixations using I-DT (Identification by Dispersion-Threshold) algorithm
#' @param x Vector of x-coordinates
#' @param y Vector of y-coordinates
#' @param timestamps Vector of timestamps (ms)
#' @param dispersion_threshold Maximum dispersion for fixation (pixels or degrees)
#' @param min_duration Minimum fixation duration (ms)
#' @return Data frame with fixation info
detect_fixations_idt <- function(x, y, timestamps, 
                                  dispersion_threshold = 25,  # pixels, adjust based on data
                                  min_duration = 100) {       # ms
  n <- length(x)
  if (n < 2) return(NULL)
  fixations <- list()
  fixation_id <- 0
  sample_labels <- rep(NA, n)  # Track which fixation each sample belongs to
  i <- 1
  while (i <= n) {
    window_start <- i
    window_end <- i
    while (window_end <= n) {
      current_x <- x[window_start:window_end]
      current_y <- y[window_start:window_end]
      disp <- calculate_dispersion(current_x, current_y)
      if (disp <= dispersion_threshold) {
        window_end <- window_end + 1
      } else {
        break
      }
    }
    window_end <- window_end - 1  # Go back to last valid point
    if (window_end > window_start) {
      duration <- timestamps[window_end] - timestamps[window_start]
      if (duration >= min_duration) {
        fixation_id <- fixation_id + 1
        fix_x <- x[window_start:window_end]
        fix_y <- y[window_start:window_end]
        fixations[[fixation_id]] <- data.frame(
          fixation_id = fixation_id,
          start_sample = window_start,
          end_sample = window_end,
          start_time = timestamps[window_start],
          end_time = timestamps[window_end],
          duration = duration,
          x_centroid = mean(fix_x, na.rm = TRUE),
          y_centroid = mean(fix_y, na.rm = TRUE),
          dispersion = calculate_dispersion(fix_x, fix_y),
          n_samples = length(fix_x)
        )
        sample_labels[window_start:window_end] <- fixation_id
        i <- window_end + 1
      } else {
        i <- i + 1
      }
    } else {
      i <- i + 1
    }
  }
  if (length(fixations) == 0) return(NULL)
  result <- do.call(rbind, fixations)
  attr(result, "sample_labels") <- sample_labels
  return(result)
}

#' Detect fixations using I-VT (Identification by Velocity-Threshold) algorithm
#' @param x Vector of x-coordinates
#' @param y Vector of y-coordinates
#' @param timestamps Vector of timestamps (ms)
#' @param velocity_threshold Threshold velocity (pixels/ms or degrees/s)
#' @param min_duration Minimum fixation duration (ms)
#' @return Data frame with fixation info
detect_fixations_ivt <- function(x, y, timestamps,
                                  velocity_threshold = 0.5,  # pixels/ms, adjust based on data
                                  min_duration = 100) {
  n <- length(x)
  if (n < 2) return(NULL)
  velocities <- calculate_velocity(x, y, timestamps)
  velocities <- c(0, velocities)  # Add 0 for first sample
  is_fixation <- velocities <= velocity_threshold
  fixations <- list()
  fixation_id <- 0
  
  in_fixation <- FALSE
  fix_start <- 1
  
  for (i in seq_len(n)) {
    if (is_fixation[i] && !in_fixation) {
      # Start of new fixation
      in_fixation <- TRUE
      fix_start <- i
    } else if (!is_fixation[i] && in_fixation) {
      # End of fixation
      in_fixation <- FALSE
      fix_end <- i - 1
      # Check minimum duration
      duration <- timestamps[fix_end] - timestamps[fix_start]
      if (duration >= min_duration && fix_end > fix_start) {
        fixation_id <- fixation_id + 1
        fix_x <- x[fix_start:fix_end]
        fix_y <- y[fix_start:fix_end]
        fixations[[fixation_id]] <- data.frame(
          fixation_id = fixation_id,
          start_sample = fix_start,
          end_sample = fix_end,
          start_time = timestamps[fix_start],
          end_time = timestamps[fix_end],
          duration = duration,
          x_centroid = mean(fix_x, na.rm = TRUE),
          y_centroid = mean(fix_y, na.rm = TRUE),
          mean_velocity = mean(velocities[fix_start:fix_end], na.rm = TRUE),
          n_samples = length(fix_x)
        )
      }
    }
  }
  # Handle fixation at end of data
  if (in_fixation) {
    fix_end <- n
    duration <- timestamps[fix_end] - timestamps[fix_start]
    if (duration >= min_duration) {
      fixation_id <- fixation_id + 1
      fix_x <- x[fix_start:fix_end]
      fix_y <- y[fix_start:fix_end]
      fixations[[fixation_id]] <- data.frame(
        fixation_id = fixation_id,
        start_sample = fix_start,
        end_sample = fix_end,
        start_time = timestamps[fix_start],
        end_time = timestamps[fix_end],
        duration = duration,
        x_centroid = mean(fix_x, na.rm = TRUE),
        y_centroid = mean(fix_y, na.rm = TRUE),
        mean_velocity = mean(velocities[fix_start:fix_end], na.rm = TRUE),
        n_samples = length(fix_x)
      )
    }
  }
  if (length(fixations) == 0) return(NULL)
  return(do.call(rbind, fixations))
}



# ----------------------------------------------------------------------------
# 7. AOI (AREA OF INTEREST) ANALYSIS
# ----------------------------------------------------------------------------

#' Define rectangular AOI
#' @param name AOI name
#' @param x_min Left boundary
#' @param x_max Right boundary
#' @param y_min Top boundary
#' @param y_max Bottom boundary
#' @return AOI object (list)
create_aoi_rect <- function(name, x_min, x_max, y_min, y_max) {
  list(
    name = name,
    type = "rectangle",
    x_min = x_min,
    x_max = x_max,
    y_min = y_min,
    y_max = y_max
  )
}

#' Define circular AOI
#' @param name AOI name
#' @param center_x Center x-coordinate
#' @param center_y Center y-coordinate
#' @param radius Radius
#' @return AOI object (list)
create_aoi_circle <- function(name, center_x, center_y, radius) {
  list(
    name = name,
    type = "circle",
    center_x = center_x,
    center_y = center_y,
    radius = radius
  )
}

#' Check if point is inside AOI
#' @param x X-coordinate
#' @param y Y-coordinate
#' @param aoi AOI object
#' @return Logical
point_in_aoi <- function(x, y, aoi) {
  if (aoi$type == "rectangle") {
    return(x >= aoi$x_min & x <= aoi$x_max & y >= aoi$y_min & y <= aoi$y_max)
  } else if (aoi$type == "circle") {
    dist <- sqrt((x - aoi$center_x)^2 + (y - aoi$center_y)^2)
    return(dist <= aoi$radius)
  }
  return(FALSE)
}

# ----------------------------------------------------------------------------
# 4. FIXATION DETECTION - I-DT ALGORITHM
# ----------------------------------------------------------------------------

#' Calculate dispersion of gaze points
#' @param x Vector of x-coordinates
#' @param y Vector of y-coordinates
#' @return Dispersion value (max distance from centroid)
calculate_dispersion <- function(x, y) {
  if (length(x) < 2) return(0)
  dispersion <- max(max(x) - min(x), max(y) - min(y))
  return(dispersion)
}



# ----------------------------------------------------------------------------
# 5. FIXATION DETECTION - I-VT ALGORITHM
# ----------------------------------------------------------------------------

# ----------------------------------------------------------------------------
# 6. SACCADE DETECTION
# ----------------------------------------------------------------------------

#' Detect saccades from fixation data
#' @param fixations Data frame from fixation detection
#' @param x Original x-coordinate vector
#' @param y Original y-coordinate vector
#' @param timestamps Original timestamp vector
#' @return Data frame with saccade info
detect_saccades <- function(fixations, x, y, timestamps) {
  if (is.null(fixations) || nrow(fixations) < 2) return(NULL)
  n_fix <- nrow(fixations)
  saccades <- list()
  for (i in 1:(n_fix - 1)) {
    sac_start <- fixations$end_sample[i] + 1
    sac_end <- fixations$start_sample[i + 1] - 1
    if (sac_end >= sac_start) {
      # Calculate saccade metrics
      start_x <- fixations$x_centroid[i]
      start_y <- fixations$y_centroid[i]
      end_x <- fixations$x_centroid[i + 1]
      end_y <- fixations$y_centroid[i + 1]
      amplitude <- sqrt((end_x - start_x)^2 + (end_y - start_y)^2)
      duration <- timestamps[sac_end] - timestamps[sac_start]
      # Calculate velocities during saccade
      sac_velocities <- calculate_velocity(
        x[sac_start:sac_end],
        y[sac_start:sac_end],
        timestamps[sac_start:sac_end]
      )
      peak_velocity <- if (length(sac_velocities) > 0) max(sac_velocities, na.rm = TRUE) else NA
      avg_velocity <- if (duration > 0) amplitude / duration else NA
      # Direction in degrees (0 = right, 90 = up)
      direction <- atan2(end_y - start_y, end_x - start_x) * (180 / pi)
      saccades[[i]] <- data.frame(
        saccade_id = i,
        start_sample = sac_start,
        end_sample = sac_end,
        start_time = timestamps[sac_start],
        end_time = timestamps[sac_end],
        duration = duration,
        amplitude = amplitude,
        peak_velocity = peak_velocity,
        avg_velocity = avg_velocity,
        direction = direction,
        start_x = start_x,
        start_y = start_y,
        end_x = end_x,
        end_y = end_y
      )
    }
  }
  if (length(saccades) == 0) return(NULL)
  return(do.call(rbind, saccades))
}

#' Calculate AOI metrics for fixations
#' @param fixations Data frame of fixations
#' @param aois List of AOI objects
#' @param stimulus_onset Stimulus onset time (ms)
#' @return Data frame with AOI metrics
calculate_aoi_metrics <- function(fixations, aois, stimulus_onset = 0) {
  if (is.null(fixations) || nrow(fixations) == 0) return(NULL)

  results <- list()

  for (aoi in aois) {
    # Check which fixations are in this AOI
    in_aoi <- sapply(seq_len(nrow(fixations)), function(i) {
      point_in_aoi(fixations$x_centroid[i], fixations$y_centroid[i], aoi)
    })
    aoi_fixations <- fixations[in_aoi, ]
    # Calculate metrics
    fixation_count <- nrow(aoi_fixations)
    total_dwell_time <- if (fixation_count > 0) sum(aoi_fixations$duration) else 0
    mean_fixation_duration <- if (fixation_count > 0) mean(aoi_fixations$duration) else NA

    # Time to first fixation
    ttff <- if (fixation_count > 0) {
      min(aoi_fixations$start_time) - stimulus_onset
    } else {
      NA
    }

    # First fixation duration
    first_fix_duration <- if (fixation_count > 0) {
      aoi_fixations$duration[which.min(aoi_fixations$start_time)]
    } else {
      NA
    }

    # Number of revisits (entries after first exit)
    revisits <- 0
    if (fixation_count > 1) {
      # Simple count of non-consecutive fixations in AOI
      aoi_fix_idx <- which(in_aoi)
      if (length(aoi_fix_idx) > 1) {
        gaps <- diff(aoi_fix_idx)
        revisits <- sum(gaps > 1)
      }
    }
    results[[aoi$name]] <- data.frame(
      aoi_name = aoi$name,
      fixation_count = fixation_count,
      total_dwell_time = total_dwell_time,
      mean_fixation_duration = mean_fixation_duration,
      time_to_first_fixation = ttff,
      first_fixation_duration = first_fix_duration,
      revisit_count = revisits,
      hit = as.integer(fixation_count > 0)
    )
  }
  return(do.call(rbind, results))
}

# ----------------------------------------------------------------------------
# 8. PUPILLOMETRY
# ----------------------------------------------------------------------------

#' Detect blinks in pupil data
#' @param pupil Vector of pupil sizes
#' @param timestamps Vector of timestamps
#' @param min_duration Minimum blink duration (ms)
#' @param velocity_threshold Velocity threshold for blink detection
#' @return Logical vector indicating blink samples
detect_blinks <- function(pupil, timestamps, 
                          min_duration = 50,
                          velocity_threshold = NULL) {
  n <- length(pupil)
  is_blink <- rep(FALSE, n)
  

  # Method 1: Missing data (NA, 0, or very small values)
  is_blink <- is.na(pupil) | pupil <= 0
  
  # Method 2: Rapid changes (if velocity threshold provided)
  if (!is.null(velocity_threshold)) {
    pupil_velocity <- c(0, abs(diff(pupil)) / diff(timestamps))
    rapid_change <- pupil_velocity > velocity_threshold
    
    # Expand rapid changes to include surrounding samples
    for (i in which(rapid_change)) {
      start <- max(1, i - 5)
      end <- min(n, i + 5)
      is_blink[start:end] <- TRUE
    }
  }
  
  return(is_blink)
}

#' Interpolate missing pupil data
#' @param pupil Vector of pupil sizes
#' @param timestamps Vector of timestamps
#' @param blinks Logical vector indicating blink samples
#' @param method Interpolation method ("linear" or "cubic")
#' @param max_gap Maximum gap to interpolate (ms)
#' @return Interpolated pupil vector
interpolate_pupil <- function(pupil, timestamps, blinks, 
                               method = "linear",
                               max_gap = 500) {
  n <- length(pupil)
  interpolated <- pupil
  # Find blink segments
  blink_segments <- rle(blinks)
  segment_end <- 0
  for (i in seq_along(blink_segments$lengths)) {
    segment_start <- segment_end + 1
    segment_end <- segment_start + blink_segments$lengths[i] - 1
    if (blink_segments$values[i]) {
      # This is a blink segment
      gap_duration <- timestamps[segment_end] - timestamps[segment_start]
      if (gap_duration <= max_gap) {
        # Find valid samples before and after
        valid_before <- max(1, segment_start - 1)
        valid_after <- min(n, segment_end + 1)
        while (valid_before > 1 && blinks[valid_before]) {
          valid_before <- valid_before - 1
        }
        while (valid_after < n && blinks[valid_after]) {
          valid_after <- valid_after + 1
        }
        if (!blinks[valid_before] && !blinks[valid_after]) {
          if (method == "linear") {
            # Linear interpolation
            interpolated[segment_start:segment_end] <- approx(
              x = c(timestamps[valid_before], timestamps[valid_after]),
              y = c(pupil[valid_before], pupil[valid_after]),
              xout = timestamps[segment_start:segment_end]
            )$y
          }
        }
      }
    }
  }
  return(interpolated)
}

#' Smooth pupil data using moving average
#' @param pupil Vector of pupil sizes
#' @param window_size Window size in samples
#' @return Smoothed pupil vector
smooth_pupil <- function(pupil, window_size = 5) {
  n <- length(pupil)
  smoothed <- rep(NA, n)
  half_window <- floor(window_size / 2)
  for (i in seq_len(n)) {
    start <- max(1, i - half_window)
    end <- min(n, i + half_window)
    smoothed[i] <- mean(pupil[start:end], na.rm = TRUE)
  }
  return(smoothed)
}

#' Apply baseline correction to pupil data
#' @param pupil Vector of pupil sizes
#' @param timestamps Vector of timestamps
#' @param baseline_start Start of baseline period (ms)
#' @param baseline_end End of baseline period (ms)
#' @param method "subtractive" or "divisive"
#' @return Baseline-corrected pupil vector
baseline_correct_pupil <- function(pupil, timestamps, 
                                    baseline_start, baseline_end,
                                    method = "subtractive") {
  # Find samples in baseline period
  baseline_idx <- timestamps >= baseline_start & timestamps <= baseline_end
  baseline_mean <- mean(pupil[baseline_idx], na.rm = TRUE)
  if (method == "subtractive") {
    # Subtractive: pupil - baseline
    corrected <- pupil - baseline_mean
  } else if (method == "divisive") {
    # Divisive: (pupil - baseline) / baseline * 100
    corrected <- (pupil - baseline_mean) / baseline_mean * 100
  } else {
    corrected <- pupil
  }
  return(corrected)
}

#' Full pupil preprocessing pipeline
#' @param pupil Vector of pupil sizes
#' @param timestamps Vector of timestamps
#' @param baseline_start Baseline period start (ms)
#' @param baseline_end Baseline period end (ms)
#' @return List with processed data and quality metrics
preprocess_pupil <- function(pupil, timestamps, 
                              baseline_start = -200, 
                              baseline_end = 0) {
  n <- length(pupil)
  blinks <- detect_blinks(pupil, timestamps)
  interpolated <- interpolate_pupil(pupil, timestamps, blinks)
  smoothed <- smooth_pupil(interpolated, window_size = 5)
  corrected <- baseline_correct_pupil(smoothed, timestamps, 
                                       baseline_start, baseline_end)
  missing_pct <- sum(is.na(pupil) | blinks) / n * 100

  return(list(
    raw = pupil,
    interpolated = interpolated,
    smoothed = smoothed,
    corrected = corrected,
    blinks = blinks,
    quality = list(
      n_samples = n,
      n_blinks = sum(rle(blinks)$values),
      missing_percent = missing_pct,
      valid = missing_pct < 50
    )
  ))
}

# ----------------------------------------------------------------------------
# 9. SUMMARY STATISTICS
# ----------------------------------------------------------------------------

#' Calculate summary statistics for fixations
#' @param fixations Data frame of fixations
#' @return Data frame with summary statistics
summarize_fixations <- function(fixations) {
  if (is.null(fixations) || nrow(fixations) == 0) {
    return(data.frame(
      n_fixations = 0,
      mean_duration = NA,
      sd_duration = NA,
      median_duration = NA,
      total_duration = 0,
      mean_dispersion = NA
    ))
  }

  data.frame(
    n_fixations = nrow(fixations),
    mean_duration = mean(fixations$duration, na.rm = TRUE),
    sd_duration = sd(fixations$duration, na.rm = TRUE),
    median_duration = median(fixations$duration, na.rm = TRUE),
    total_duration = sum(fixations$duration, na.rm = TRUE),
    mean_dispersion = mean(fixations$dispersion, na.rm = TRUE)
  )
}

#' Calculate summary statistics for saccades
#' @param saccades Data frame of saccades
#' @return Data frame with summary statistics
summarize_saccades <- function(saccades) {
  if (is.null(saccades) || nrow(saccades) == 0) {
    return(data.frame(
      n_saccades = 0,
      mean_amplitude = NA,
      sd_amplitude = NA,
      mean_duration = NA,
      mean_peak_velocity = NA,
      mean_avg_velocity = NA
    ))
  }

  data.frame(
    n_saccades = nrow(saccades),
    mean_amplitude = mean(saccades$amplitude, na.rm = TRUE),
    sd_amplitude = sd(saccades$amplitude, na.rm = TRUE),
    mean_duration = mean(saccades$duration, na.rm = TRUE),
    mean_peak_velocity = mean(saccades$peak_velocity, na.rm = TRUE),
    mean_avg_velocity = mean(saccades$avg_velocity, na.rm = TRUE)
  )
}

# ----------------------------------------------------------------------------
# 10. VISUALIZATION (base R graphics)
# ----------------------------------------------------------------------------

#' Plot scanpath
#' @param fixations Data frame of fixations
#' @param screen_width Screen width for plot limits
#' @param screen_height Screen height for plot limits
#' @param main Plot title
plot_scanpath <- function(raw, fixations, screen_width = 1920, screen_height = 1080, 
                          main = "Scanpath") {
  plt <- ggplot() +
    geom_path(data = raw, aes(x = x, y = y), color = "gray80", alpha = 0.8) +
    geom_path(data = fixations, aes(x = x_centroid, y = y_centroid), color = "gray50") +
    geom_point(data = fixations, aes(x = x_centroid, y = y_centroid, 
                                     size = duration, color = factor(fixation_id)),
                alpha = 0.7) +
    geom_text(data = fixations, aes(x = x_centroid, y = y_centroid, label = fixation_id),
              size = 3, color = "white") +
    scale_y_reverse(limits = c(screen_height, 0)) +
    scale_x_continuous(limits = c(0, screen_width)) +
    coord_fixed() +
    theme_minimal() +
    guides(color = "none", size = "none") +
    labs(title = main, x = "X (px)", y = "Y (px)")
    return(plt)
}

#' Create simple heatmap using base R
#' @param x Vector of x-coordinates (can be raw gaze or fixation centroids)
#' @param y Vector of y-coordinates
#' @param weights Optional weights (e.g., fixation durations)
#' @param screen_width Screen width
#' @param screen_height Screen height
#' @param resolution Grid resolution
#' @param main Plot title
plot_heatmap <- function(x, y, weights = NULL, 
                         screen_width = 1920, screen_height = 1080,
                         resolution = 50, main = "Gaze Heatmap") {
  # Create 2D histogram
  x_breaks <- seq(0, screen_width, length.out = resolution + 1)
  y_breaks <- seq(0, screen_height, length.out = resolution + 1)

  x_bin <- findInterval(x, x_breaks)
  y_bin <- findInterval(y, y_breaks)

  # Create count matrix
  heatmap_matrix <- matrix(0, nrow = resolution, ncol = resolution)
  
  for (i in seq_along(x)) {
    if (x_bin[i] >= 1 && x_bin[i] <= resolution &&
        y_bin[i] >= 1 && y_bin[i] <= resolution) {
      weight <- if (!is.null(weights)) weights[i] else 1
      heatmap_matrix[y_bin[i], x_bin[i]] <- heatmap_matrix[y_bin[i], x_bin[i]] + weight
    }
  }

  # Simple Gaussian smoothing
  smooth_kernel <- function(mat, sigma = 2) {
    n <- nrow(mat)
    m <- ncol(mat)
    result <- mat

    for (i in 1:n) {
      for (j in 1:m) {
        total <- 0
        weight_sum <- 0
        for (di in -2:2) {
          for (dj in -2:2) {
            ni <- i + di
            nj <- j + dj
            if (ni >= 1 && ni <= n && nj >= 1 && nj <= m) {
              w <- exp(-(di^2 + dj^2) / (2 * sigma^2))
              total <- total + mat[ni, nj] * w
              weight_sum <- weight_sum + w
            }
          }
        }
        result[i, j] <- total / weight_sum
      }
    }
    return(result)
  }
  heatmap_smoothed <- smooth_kernel(heatmap_matrix)
  colors <- colorRampPalette(c("white", "yellow", "orange", "red", "darkred"))(100)

  image(x = x_breaks[-length(x_breaks)], 
        y = y_breaks[-length(y_breaks)],
        z = t(heatmap_smoothed),
        col = colors,
        xlab = "X (pixels)", ylab = "Y (pixels)",
        main = main,
        useRaster = TRUE)
}

#' Plot pupil time series
#' @param timestamps Vector of timestamps
#' @param pupil_raw Raw pupil data
#' @param pupil_processed Processed pupil data (optional)
#' @param main Plot title
plot_pupil_timeseries <- function(timestamps, pupil_raw, 
                                   pupil_processed = NULL,
                                   main = "Pupil Size Over Time") {
  ylim <- range(c(pupil_raw, pupil_processed), na.rm = TRUE)
  
  plot(timestamps, pupil_raw, type = "l", col = "gray70",
       xlab = "Time (ms)", ylab = "Pupil Size",
       main = main, ylim = ylim)
  
  if (!is.null(pupil_processed)) {
    lines(timestamps, pupil_processed, col = "blue", lwd = 2)
    legend("topright", legend = c("Raw", "Processed"),
           col = c("gray70", "blue"), lwd = c(1, 2))
  }
}

# ----------------------------------------------------------------------------
# 11. EXAMPLE USAGE
# ----------------------------------------------------------------------------

# Example: Complete analysis pipeline
run_example_analysis <- function() {
  cat("Eye-tracking Analysis Example\n")
  cat("============================\n\n")
  
  # Simulate some eye-tracking data
  set.seed(42)
  n_samples <- 1000
  sampling_rate <- 60  # Hz
  
  # Generate timestamps
  timestamps <- seq(0, (n_samples - 1) * (1000 / sampling_rate), 
                    by = 1000 / sampling_rate)
  
  # Generate x, y coordinates with fixations and saccades
  # Start with fixation at center
  x <- rep(960, n_samples)
  y <- rep(540, n_samples)
  
  # Add some fixations at different locations
  fixation_locations <- list(
    list(x = 960, y = 540, start = 1, end = 150),
    list(x = 500, y = 300, start = 160, end = 300),
    list(x = 1400, y = 700, start = 310, end = 500),
    list(x = 800, y = 200, start = 510, end = 700),
    list(x = 1100, y = 500, start = 710, end = 900)
  )
  
  for (fix in fixation_locations) {
    noise_x <- rnorm(fix$end - fix$start + 1, 0, 10)
    noise_y <- rnorm(fix$end - fix$start + 1, 0, 10)
    x[fix$start:fix$end] <- fix$x + noise_x
    y[fix$start:fix$end] <- fix$y + noise_y
  }
  
  # Interpolate saccades
  for (i in 1:(length(fixation_locations) - 1)) {
    sac_start <- fixation_locations[[i]]$end + 1
    sac_end <- fixation_locations[[i + 1]]$start - 1
    
    if (sac_end > sac_start) {
      x[sac_start:sac_end] <- seq(
        fixation_locations[[i]]$x,
        fixation_locations[[i + 1]]$x,
        length.out = sac_end - sac_start + 1
      )
      y[sac_start:sac_end] <- seq(
        fixation_locations[[i]]$y,
        fixation_locations[[i + 1]]$y,
        length.out = sac_end - sac_start + 1
      )
    }
  }
  
  # Generate pupil data
  pupil <- 4 + 0.5 * sin(timestamps / 1000) + rnorm(n_samples, 0, 0.1)
  # Add some blinks
  pupil[200:210] <- NA
  pupil[600:615] <- NA
  
  cat("1. Simulated data generated:\n")
  cat(sprintf("   - %d samples at %d Hz\n", n_samples, sampling_rate))
  cat(sprintf("   - Duration: %.1f seconds\n\n", max(timestamps) / 1000))
  
  # Detect fixations using I-DT
  fixations <- detect_fixations_idt(x, y, timestamps, 
                                     dispersion_threshold = 50,
                                     min_duration = 100)
  
  cat("2. Fixation detection (I-DT algorithm):\n")
  cat(sprintf("   - Detected %d fixations\n", nrow(fixations)))
  cat(sprintf("   - Mean duration: %.1f ms\n", mean(fixations$duration)))
  cat(sprintf("   - Total dwell time: %.1f ms\n\n", sum(fixations$duration)))
  
  # Detect saccades
  saccades <- detect_saccades(fixations, x, y, timestamps)
  
  cat("3. Saccade detection:\n")
  cat(sprintf("   - Detected %d saccades\n", nrow(saccades)))
  cat(sprintf("   - Mean amplitude: %.1f pixels\n", mean(saccades$amplitude)))
  cat(sprintf("   - Mean duration: %.1f ms\n\n", mean(saccades$duration)))
  
  # Define AOIs
  aois <- list(
    create_aoi_rect("Left", 0, 640, 0, 1080),
    create_aoi_rect("Center", 640, 1280, 0, 1080),
    create_aoi_rect("Right", 1280, 1920, 0, 1080)
  )
  
  # Calculate AOI metrics
  aoi_metrics <- calculate_aoi_metrics(fixations, aois)
  
  cat("4. AOI Analysis:\n")
  print(aoi_metrics[, c("aoi_name", "fixation_count", "total_dwell_time", 
                        "time_to_first_fixation")])
  cat("\n")
  
  # Preprocess pupil data
  pupil_result <- preprocess_pupil(pupil, timestamps)
  
  cat("5. Pupil preprocessing:\n")
  cat(sprintf("   - Missing data: %.1f%%\n", pupil_result$quality$missing_percent))
  cat(sprintf("   - Number of blinks: %d\n", pupil_result$quality$n_blinks))
  cat(sprintf("   - Data quality valid: %s\n\n", pupil_result$quality$valid))
  
  # Create visualizations
  cat("6. Creating visualizations...\n")
  
  # Set up multi-panel plot
  par(mfrow = c(2, 2), mar = c(4, 4, 3, 1))
  
  # Scanpath
  plot_scanpath(fixations, main = "Scanpath")
  
  # Heatmap
  plot_heatmap(fixations$x_centroid, fixations$y_centroid, 
               weights = fixations$duration,
               main = "Fixation Heatmap")
  
  # Pupil time series
  plot_pupil_timeseries(timestamps, pupil_result$raw, 
                        pupil_result$corrected,
                        main = "Pupil Size")
  
  # Fixation duration histogram
  hist(fixations$duration, breaks = 20, col = "steelblue",
       main = "Fixation Duration Distribution",
       xlab = "Duration (ms)", ylab = "Count")
  
  par(mfrow = c(1, 1))
  
  cat("\nAnalysis complete!\n")
  
  # Return results
  return(list(
    fixations = fixations,
    saccades = saccades,
    aoi_metrics = aoi_metrics,
    pupil = pupil_result
  ))
}

# Run example if this script is sourced directly
if (interactive()) {
  cat("\nTo run the example analysis, call: run_example_analysis()\n")
}
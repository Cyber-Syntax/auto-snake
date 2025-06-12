#define PY_SSIZE_T_CLEAN
#include <Python.h>
#include <numpy/arrayobject.h>
#include <opencv2/opencv.hpp>
#include <thread>
#include <future>
#include <vector>
#include <chrono>
#include <mutex>
#include <iostream>
#include <algorithm>

PyDoc_STRVAR(automation_core_doc,
    "High-performance C++ automation core with true parallelism.\n"
    "Provides GIL-free template matching, health detection, and image processing.");

// Thread-safe logging
std::mutex log_mutex;
void thread_safe_log(const std::string& message) {
    std::lock_guard<std::mutex> lock(log_mutex);
    auto now = std::chrono::system_clock::now();
    auto time_t = std::chrono::system_clock::to_time_t(now);
    auto tm = *std::localtime(&time_t);

    printf("[%04d-%02d-%02d %02d:%02d:%02d C++] %s\n",
           tm.tm_year + 1900, tm.tm_mon + 1, tm.tm_mday,
           tm.tm_hour, tm.tm_min, tm.tm_sec, message.c_str());
    fflush(stdout);
}

// Structure for template matching result
struct MatchResult {
    double max_val;
    cv::Point max_loc;
    double confidence;
    bool found;
    int template_id;
    double processing_time_ms;
};

// Structure for health detection result
struct HealthResult {
    double health_percentage;
    bool is_empty;
    bool is_critical;
    double processing_time_ms;
    cv::Point health_location;
    bool health_bar_found;
};

// Convert PyArrayObject to cv::Mat
cv::Mat pyarray_to_mat(PyArrayObject* input) {
    if (input == nullptr) {
        throw std::runtime_error("Input array is null");
    }

    int ndim = PyArray_NDIM(input);
    if (ndim < 2 || ndim > 3) {
        throw std::runtime_error("Array must be 2D or 3D");
    }

    int height = PyArray_DIM(input, 0);
    int width = PyArray_DIM(input, 1);
    int channels = (ndim == 3) ? PyArray_DIM(input, 2) : 1;

    // Ensure array is contiguous
    if (!PyArray_IS_C_CONTIGUOUS(input)) {
        PyArrayObject* contiguous = (PyArrayObject*)PyArray_NewCopy(input, NPY_CORDER);
        if (contiguous == nullptr) {
            throw std::runtime_error("Failed to create contiguous array");
        }
        input = contiguous;
    }

    cv::Mat mat;
    int cv_type;

    if (channels == 1) {
        cv_type = CV_8UC1;
    } else if (channels == 3) {
        cv_type = CV_8UC3;
    } else if (channels == 4) {
        cv_type = CV_8UC4;
    } else {
        throw std::runtime_error("Unsupported number of channels");
    }

    mat = cv::Mat(height, width, cv_type, PyArray_DATA(input));
    return mat.clone(); // Make a copy to avoid memory issues
}

// Parallel template matching function (GIL-free)
MatchResult parallel_template_match(const cv::Mat& image, const cv::Mat& template_img,
                                  int method, double threshold, int template_id) {
    auto start = std::chrono::high_resolution_clock::now();

    MatchResult result;
    result.template_id = template_id;
    result.found = false;
    result.max_val = 0.0;
    result.confidence = 0.0;
    result.max_loc = cv::Point(0, 0);

    try {
        if (image.empty() || template_img.empty()) {
            thread_safe_log("Empty image or template in parallel_template_match");
            return result;
        }

        if (template_img.rows > image.rows || template_img.cols > image.cols) {
            thread_safe_log("Template larger than image");
            return result;
        }

        cv::Mat match_result;
        cv::matchTemplate(image, template_img, match_result, method);

        double min_val, max_val;
        cv::Point min_loc, max_loc;
        cv::minMaxLoc(match_result, &min_val, &max_val, &min_loc, &max_loc);

        result.max_val = max_val;
        result.max_loc = max_loc;
        result.confidence = max_val;
        result.found = max_val >= threshold;

    } catch (const cv::Exception& e) {
        thread_safe_log("OpenCV error in template matching: " + std::string(e.what()));
    } catch (const std::exception& e) {
        thread_safe_log("Error in template matching: " + std::string(e.what()));
    }

    auto end = std::chrono::high_resolution_clock::now();
    auto duration = std::chrono::duration_cast<std::chrono::microseconds>(end - start);
    result.processing_time_ms = duration.count() / 1000.0;

    return result;
}

// Multi-template matching with true parallelism
std::vector<MatchResult> multi_template_match(const cv::Mat& image,
                                            const std::vector<cv::Mat>& templates,
                                            const std::vector<double>& thresholds,
                                            int method) {
    std::vector<std::future<MatchResult>> futures;
    std::vector<MatchResult> results;

    if (templates.size() != thresholds.size()) {
        thread_safe_log("Template and threshold vectors size mismatch");
        return results;
    }

    // Launch parallel template matching tasks
    for (size_t i = 0; i < templates.size(); ++i) {
        futures.push_back(std::async(std::launch::async, parallel_template_match,
                                   std::cref(image), std::cref(templates[i]),
                                   method, thresholds[i], static_cast<int>(i)));
    }

    // Collect results
    for (auto& future : futures) {
        try {
            results.push_back(future.get());
        } catch (const std::exception& e) {
            thread_safe_log("Error getting template match result: " + std::string(e.what()));
            MatchResult error_result = {0.0, cv::Point(0, 0), 0.0, false, -1, 0.0};
            results.push_back(error_result);
        }
    }

    return results;
}

// Advanced health detection with parallel processing
HealthResult detect_health_parallel(const cv::Mat& screenshot, const cv::Mat& health_bar_template,
                                  const cv::Mat& empty_health_template, double health_threshold) {
    auto start = std::chrono::high_resolution_clock::now();

    HealthResult result;
    result.health_percentage = 0.0;
    result.is_empty = false;
    result.is_critical = false;
    result.processing_time_ms = 0.0;
    result.health_location = cv::Point(0, 0);
    result.health_bar_found = false;

    try {
        if (screenshot.empty() || health_bar_template.empty() || empty_health_template.empty()) {
            thread_safe_log("Empty input in health detection");
            return result;
        }

        // Parallel health bar detection
        std::future<MatchResult> health_bar_future = std::async(std::launch::async,
            parallel_template_match, std::cref(screenshot), std::cref(health_bar_template),
            cv::TM_CCOEFF_NORMED, 0.7, 0);

        std::future<MatchResult> empty_health_future = std::async(std::launch::async,
            parallel_template_match, std::cref(screenshot), std::cref(empty_health_template),
            cv::TM_CCOEFF_NORMED, 0.8, 1);

        // Get results
        MatchResult health_bar_result = health_bar_future.get();
        MatchResult empty_health_result = empty_health_future.get();

        result.health_bar_found = health_bar_result.found;
        result.health_location = health_bar_result.max_loc;

        // Process health bar if found
        if (health_bar_result.found) {
            cv::Point health_loc = health_bar_result.max_loc;
            cv::Size template_size = health_bar_template.size();

            // Extract health bar region with bounds checking
            cv::Rect health_roi(health_loc.x, health_loc.y, template_size.width, template_size.height);

            // Ensure ROI is within image bounds
            health_roi.x = std::max(0, health_roi.x);
            health_roi.y = std::max(0, health_roi.y);
            health_roi.width = std::min(health_roi.width, screenshot.cols - health_roi.x);
            health_roi.height = std::min(health_roi.height, screenshot.rows - health_roi.y);

            if (health_roi.width > 0 && health_roi.height > 0) {
                cv::Mat health_region = screenshot(health_roi);

                // Analyze health percentage using color analysis
                cv::Mat hsv;
                cv::cvtColor(health_region, hsv, cv::COLOR_BGR2HSV);

                // Define red color range for health (two ranges for red hue wrap-around)
                cv::Scalar lower_red1(0, 120, 70);
                cv::Scalar upper_red1(10, 255, 255);
                cv::Scalar lower_red2(170, 120, 70);
                cv::Scalar upper_red2(180, 255, 255);

                cv::Mat mask1, mask2, red_mask;
                cv::inRange(hsv, lower_red1, upper_red1, mask1);
                cv::inRange(hsv, lower_red2, upper_red2, mask2);
                red_mask = mask1 + mask2;

                int red_pixels = cv::countNonZero(red_mask);
                int total_pixels = health_region.rows * health_region.cols;

                if (total_pixels > 0) {
                    result.health_percentage = static_cast<double>(red_pixels) / total_pixels;
                } else {
                    result.health_percentage = 0.0;
                }
            }
        }

        // Check for empty health
        result.is_empty = empty_health_result.found || result.health_percentage < 0.05;
        result.is_critical = result.health_percentage < health_threshold;

    } catch (const cv::Exception& e) {
        thread_safe_log("OpenCV error in health detection: " + std::string(e.what()));
    } catch (const std::exception& e) {
        thread_safe_log("Error in health detection: " + std::string(e.what()));
    }

    auto end = std::chrono::high_resolution_clock::now();
    auto duration = std::chrono::duration_cast<std::chrono::microseconds>(end - start);
    result.processing_time_ms = duration.count() / 1000.0;

    return result;
}

// Python wrapper for parallel health detection
PyObject* cpp_detect_health_parallel(PyObject* self, PyObject* args) {
    PyArrayObject* screenshot_array = nullptr;
    PyArrayObject* health_template_array = nullptr;
    PyArrayObject* empty_template_array = nullptr;
    double health_threshold = 0.3;

    if (!PyArg_ParseTuple(args, "O!O!O!d",
                         &PyArray_Type, &screenshot_array,
                         &PyArray_Type, &health_template_array,
                         &PyArray_Type, &empty_template_array,
                         &health_threshold)) {
        return NULL;
    }

    HealthResult result;

    // Release GIL for true parallelism
    Py_BEGIN_ALLOW_THREADS

    try {
        cv::Mat screenshot = pyarray_to_mat(screenshot_array);
        cv::Mat health_template = pyarray_to_mat(health_template_array);
        cv::Mat empty_template = pyarray_to_mat(empty_template_array);

        result = detect_health_parallel(screenshot, health_template, empty_template, health_threshold);

        std::string log_msg = "Health detection completed in " +
                             std::to_string(result.processing_time_ms) + "ms, " +
                             "health: " + std::to_string(result.health_percentage * 100) + "%";
        thread_safe_log(log_msg);

    } catch (const std::exception& e) {
        thread_safe_log("Error in health detection: " + std::string(e.what()));
        result = {0.0, false, false, 0.0, cv::Point(0, 0), false};
    }

    Py_END_ALLOW_THREADS

    // Return result as Python dictionary
    PyObject* result_dict = PyDict_New();
    if (result_dict == NULL) {
        return NULL;
    }

    PyDict_SetItemString(result_dict, "health_percentage", PyFloat_FromDouble(result.health_percentage));
    PyDict_SetItemString(result_dict, "is_empty", PyBool_FromLong(result.is_empty));
    PyDict_SetItemString(result_dict, "is_critical", PyBool_FromLong(result.is_critical));
    PyDict_SetItemString(result_dict, "processing_time_ms", PyFloat_FromDouble(result.processing_time_ms));
    PyDict_SetItemString(result_dict, "health_bar_found", PyBool_FromLong(result.health_bar_found));

    PyObject* location_tuple = PyTuple_New(2);
    PyTuple_SetItem(location_tuple, 0, PyLong_FromLong(result.health_location.x));
    PyTuple_SetItem(location_tuple, 1, PyLong_FromLong(result.health_location.y));
    PyDict_SetItemString(result_dict, "health_location", location_tuple);

    return result_dict;
}

// Python wrapper for multi-template matching
PyObject* cpp_multi_template_match(PyObject* self, PyObject* args) {
    PyArrayObject* image_array = nullptr;
    PyObject* template_list = nullptr;
    PyObject* threshold_list = nullptr;
    int method = cv::TM_CCOEFF_NORMED;

    if (!PyArg_ParseTuple(args, "O!O!O!|i",
                         &PyArray_Type, &image_array,
                         &PyList_Type, &template_list,
                         &PyList_Type, &threshold_list,
                         &method)) {
        return NULL;
    }

    std::vector<MatchResult> results;

    try {
        cv::Mat image = pyarray_to_mat(image_array);
        std::vector<cv::Mat> templates;
        std::vector<double> thresholds;

        Py_ssize_t template_count = PyList_Size(template_list);
        Py_ssize_t threshold_count = PyList_Size(threshold_list);

        if (template_count != threshold_count) {
            PyErr_SetString(PyExc_ValueError, "Template and threshold lists must have the same size");
            return NULL;
        }

        // Convert Python lists to C++ vectors
        for (Py_ssize_t i = 0; i < template_count; ++i) {
            PyObject* template_item = PyList_GetItem(template_list, i);
            PyObject* threshold_item = PyList_GetItem(threshold_list, i);

            if (PyArray_Check(template_item)) {
                cv::Mat template_mat = pyarray_to_mat((PyArrayObject*)template_item);
                templates.push_back(template_mat);
                thresholds.push_back(PyFloat_AsDouble(threshold_item));
            }
        }

        if (templates.empty()) {
            PyErr_SetString(PyExc_ValueError, "No valid templates provided");
            return NULL;
        }

        // Release GIL for parallel processing
        Py_BEGIN_ALLOW_THREADS

        // Perform parallel template matching
        results = multi_template_match(image, templates, thresholds, method);

        std::string log_msg = "Multi-template matching completed for " +
                             std::to_string(templates.size()) + " templates";
        thread_safe_log(log_msg);

        Py_END_ALLOW_THREADS

    } catch (const std::exception& e) {
        std::string error_msg = "Error in multi-template matching: " + std::string(e.what());
        thread_safe_log(error_msg);
        PyErr_SetString(PyExc_RuntimeError, error_msg.c_str());
        return NULL;
    }

    // Convert results to Python list
    PyObject* result_list = PyList_New(results.size());
    if (result_list == NULL) {
        return NULL;
    }

    for (size_t i = 0; i < results.size(); ++i) {
        PyObject* match_dict = PyDict_New();
        if (match_dict == NULL) {
            Py_DECREF(result_list);
            return NULL;
        }

        PyDict_SetItemString(match_dict, "max_val", PyFloat_FromDouble(results[i].max_val));
        PyDict_SetItemString(match_dict, "confidence", PyFloat_FromDouble(results[i].confidence));
        PyDict_SetItemString(match_dict, "found", PyBool_FromLong(results[i].found));
        PyDict_SetItemString(match_dict, "template_id", PyLong_FromLong(results[i].template_id));
        PyDict_SetItemString(match_dict, "processing_time_ms", PyFloat_FromDouble(results[i].processing_time_ms));

        PyObject* location = PyTuple_New(2);
        PyTuple_SetItem(location, 0, PyLong_FromLong(results[i].max_loc.x));
        PyTuple_SetItem(location, 1, PyLong_FromLong(results[i].max_loc.y));
        PyDict_SetItemString(match_dict, "location", location);

        PyList_SetItem(result_list, i, match_dict);
    }

    return result_list;
}

// Batch screenshot processing
PyObject* cpp_batch_process_screenshots(PyObject* self, PyObject* args) {
    PyObject* screenshot_list = nullptr;
    PyArrayObject* health_template = nullptr;
    PyArrayObject* respawn_template = nullptr;
    double health_threshold = 0.3;

    if (!PyArg_ParseTuple(args, "O!O!O!d",
                         &PyList_Type, &screenshot_list,
                         &PyArray_Type, &health_template,
                         &PyArray_Type, &respawn_template,
                         &health_threshold)) {
        return NULL;
    }

    PyObject* results = PyList_New(0);
    if (results == NULL) {
        return NULL;
    }

    try {
        cv::Mat health_tmpl = pyarray_to_mat(health_template);
        cv::Mat respawn_tmpl = pyarray_to_mat(respawn_template);

        Py_ssize_t screenshot_count = PyList_Size(screenshot_list);
        std::vector<std::future<PyObject*>> futures;

        // Release GIL for batch processing
        Py_BEGIN_ALLOW_THREADS

        // Convert screenshots and launch parallel processing
        for (Py_ssize_t i = 0; i < screenshot_count; ++i) {
            Py_BLOCK_THREADS

            PyObject* screenshot_item = PyList_GetItem(screenshot_list, i);

            if (PyArray_Check(screenshot_item)) {
                cv::Mat screenshot = pyarray_to_mat((PyArrayObject*)screenshot_item);

                // Launch parallel processing
                auto future = std::async(std::launch::async, [screenshot, health_tmpl, respawn_tmpl, health_threshold]() -> PyObject* {
                    try {
                        // Perform both health and respawn detection in parallel
                        std::future<MatchResult> health_future = std::async(std::launch::async,
                            parallel_template_match, std::cref(screenshot), std::cref(health_tmpl),
                            cv::TM_CCOEFF_NORMED, 0.7, 0);

                        std::future<MatchResult> respawn_future = std::async(std::launch::async,
                            parallel_template_match, std::cref(screenshot), std::cref(respawn_tmpl),
                            cv::TM_CCOEFF_NORMED, 0.8, 1);

                        MatchResult health_result = health_future.get();
                        MatchResult respawn_result = respawn_future.get();

                        // Create result dictionary
                        PyObject* result_dict = PyDict_New();
                        if (result_dict != NULL) {
                            PyDict_SetItemString(result_dict, "health_found", PyBool_FromLong(health_result.found));
                            PyDict_SetItemString(result_dict, "health_confidence", PyFloat_FromDouble(health_result.confidence));
                            PyDict_SetItemString(result_dict, "respawn_found", PyBool_FromLong(respawn_result.found));
                            PyDict_SetItemString(result_dict, "respawn_confidence", PyFloat_FromDouble(respawn_result.confidence));
                        }

                        return result_dict;

                    } catch (const std::exception& e) {
                        thread_safe_log("Error in batch processing item: " + std::string(e.what()));
                        return Py_None;
                    }
                });

                futures.push_back(std::move(future));
            }

            Py_UNBLOCK_THREADS
        }

        // Collect results
        for (auto& future : futures) {
            try {
                PyObject* result = future.get();
                if (result != nullptr) {
                    Py_BLOCK_THREADS
                    PyList_Append(results, result);
                    Py_UNBLOCK_THREADS
                }
            } catch (const std::exception& e) {
                thread_safe_log("Error getting batch result: " + std::string(e.what()));
            }
        }

        std::string log_msg = "Batch processing completed for " +
                             std::to_string(futures.size()) + " screenshots";
        thread_safe_log(log_msg);

        Py_END_ALLOW_THREADS

    } catch (const std::exception& e) {
        std::string error_msg = "Error in batch processing: " + std::string(e.what());
        thread_safe_log(error_msg);
        PyErr_SetString(PyExc_RuntimeError, error_msg.c_str());
        Py_DECREF(results);
        return NULL;
    }

    return results;
}

// Benchmark function for testing performance
PyObject* cpp_benchmark_template_matching(PyObject* self, PyObject* args) {
    PyArrayObject* image_array = nullptr;
    PyArrayObject* template_array = nullptr;
    int iterations = 100;

    if (!PyArg_ParseTuple(args, "O!O!|i",
                         &PyArray_Type, &image_array,
                         &PyArray_Type, &template_array,
                         &iterations)) {
        return NULL;
    }

    double total_time = 0.0;

    Py_BEGIN_ALLOW_THREADS

    try {
        cv::Mat image = pyarray_to_mat(image_array);
        cv::Mat template_img = pyarray_to_mat(template_array);

        auto start = std::chrono::high_resolution_clock::now();

        for (int i = 0; i < iterations; ++i) {
            cv::Mat result;
            cv::matchTemplate(image, template_img, result, cv::TM_CCOEFF_NORMED);

            double min_val, max_val;
            cv::Point min_loc, max_loc;
            cv::minMaxLoc(result, &min_val, &max_val, &min_loc, &max_loc);
        }

        auto end = std::chrono::high_resolution_clock::now();
        auto duration = std::chrono::duration_cast<std::chrono::microseconds>(end - start);
        total_time = duration.count() / 1000.0; // Convert to milliseconds

        std::string log_msg = "Benchmark completed: " + std::to_string(iterations) +
                             " iterations in " + std::to_string(total_time) + "ms";
        thread_safe_log(log_msg);

    } catch (const std::exception& e) {
        thread_safe_log("Error in benchmark: " + std::string(e.what()));
    }

    Py_END_ALLOW_THREADS

    PyObject* result_dict = PyDict_New();
    PyDict_SetItemString(result_dict, "total_time_ms", PyFloat_FromDouble(total_time));
    PyDict_SetItemString(result_dict, "iterations", PyLong_FromLong(iterations));
    PyDict_SetItemString(result_dict, "avg_time_ms", PyFloat_FromDouble(total_time / iterations));

    return result_dict;
}

// Method definitions
static PyMethodDef automation_core_methods[] = {
    {"detect_health_parallel", cpp_detect_health_parallel, METH_VARARGS,
     "Detect health status using parallel processing with GIL released"},
    {"multi_template_match", cpp_multi_template_match, METH_VARARGS,
     "Perform multiple template matching operations in parallel"},
    {"batch_process_screenshots", cpp_batch_process_screenshots, METH_VARARGS,
     "Process multiple screenshots in parallel for health and respawn detection"},
    {"benchmark_template_matching", cpp_benchmark_template_matching, METH_VARARGS,
     "Benchmark template matching performance"},
    {NULL, NULL, 0, NULL}
};

// Module definition
static struct PyModuleDef automation_core_module = {
    PyModuleDef_HEAD_INIT,
    "automation_core",
    automation_core_doc,
    -1,
    automation_core_methods
};

// Module initialization
PyMODINIT_FUNC PyInit_automation_core(void) {
    PyObject* module = PyModule_Create(&automation_core_module);
    if (module == NULL) {
        return NULL;
    }

    // Initialize NumPy
    import_array();
    if (PyErr_Occurred()) {
        Py_DECREF(module);
        return NULL;
    }

    thread_safe_log("C++ automation core module initialized successfully");

    return module;
}

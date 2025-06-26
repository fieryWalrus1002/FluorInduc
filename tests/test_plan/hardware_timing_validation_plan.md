# Hardware Timing Validation Plan
### Author: Magnus Wood
### Revision Date: 2025-06-26

## Purpose

## Scope

## System Overview

## Problem Statement

## Jitter Modeling and Assumptions

## Test Cases

## Evaluation Criteria


## Tools and Data Collection

## Results Reporting

## Appendices


################# end of template #################
Fill it in, with some of what I've alrady written, and some new content.


## framing the problem:
1. **Problem**: I want to ensure that a device's timing is consistent with its design specifications.
2. **Context**: The device is a fluorescence induction measurement system, which involves hardware events like LED activations and shutter operations. It triggers an asynchronous measurement process, and performs multiple hardware operations in a sequence. The timing of these operations is critical for accurate measurements.
3. Goal: To verify that the timing of hardware events aligns with the expected timing defined in the device's protocol.

## Problem Statement
You are testing a device that performs fluorescence induction measurements. The device operates by triggering hardware events such as LED activations and shutter operations, which are critical for the measurement process.
You need to ensure that the timing of these hardware events is consistent with the expected timing defined in the device's protocol.


## Accounting for Timing Jitter
Timing jitter refers to the variability in timing of hardware events due to system-level noise. In this context, we need to account for jitter when:
- Measuring the time intervals between hardware events.
- Comparing the measured intervals to expected values.
- Accounting for known timing jitter — that is, system-level noise from sources like LED turn-on delays or shutter mechanics.
- Rejecting measurements that fall outside the expected range, taking jitter into account.
## Test Cases
1. **Test Case 1**: Measure the time between LED activation and shutter opening.
   - **Input**: Trigger LED activation, then shutter opening.
   - **Expected Output**: The measured time should be within the expected range defined by the device's protocol.


## Test Plan
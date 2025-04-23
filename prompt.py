#!/usr/bin/env python3

from __future__ import annotations
from yandex_cloud_ml_sdk import YCloudML
import os
import ast
import ast_visitor

class MLMessager:

    def __init__(self, ML_API_KEY, FOLDER_ID, prompt_filename):
        self.ML_API_KEY = ML_API_KEY
        self.functions_delimeter = '```'
        self.text_delimeter = "====================="
        self.FOLDER_ID = FOLDER_ID
        self.sdk = YCloudML(
            folder_id=self.FOLDER_ID,
            auth=self.ML_API_KEY,
        )
        with open(prompt_filename) as f:
            self.base_message = [{"role":"system", "text":f.read()}]
        
        self.function_list = ["add_meeting", "delete_meeting", "find_slots", "change_meeting"]

    # Here we have array of calls from parse_results
    def send_message(self, user_message):
        current_message = self.base_message + [{"role":"user", "text":user_message}]
        result = (
            self.sdk.models.completions("yandexgpt").configure(temperature=0.5).run(current_message)
        )
        results = []
        for alternative in result:
            print(alternative)
            results.append(self.parse_results(alternative.text))
        return results

    # returns pair of call list and text for user
    # You can Just use this call as it: res[1] - is Text, and iterate over res[0], i.e. function_call_name, args = res[0][0] then you just do this function_map[function_call_name](*args) 
    def parse_results(self, text):
        splitted_parts = text.split(self.text_delimeter)
        results = []
        for texted_funcs in splitted_parts[0].split():
            if not any([i in texted_funcs for i in self.function_list]):
                continue
            visitor = ast_visitor.MyVisitor()
            visitor.visit(ast.parse(texted_funcs))
            results.append((visitor.function_name, visitor.args))
        return [results, splitted_parts[1]]


from encode import encode_data
import json
import random
import ast
import matplotlib.pyplot as plt

if __name__ == "__main__":

    with open("data/LAMMPSData/lammps_data.json", "r") as file:
        lammps_data = json.load(file)
        num_commands = len(lammps_data)
        commands_indices = random.sample(range(num_commands), 100)
        commands_list = [lammps_data[i]['command'] for i in commands_indices]

        chunks_vector_store = encode_data(lammps_data)
        scores = {}
        mrr = {}
        for k in [1, 3, 5, 10, 15, 20, 25]:
            correct_count = 0
            rr_total = 0
            for command in commands_list:
                chunks_query_retriever = chunks_vector_store.as_retriever(search_kwargs={"k": k})
                query = f"What are the restriction and description for {command} command"
                docs = chunks_query_retriever.invoke(query)
                context = [doc.page_content for doc in docs]
                context = [ast.literal_eval(context[i]) for i in range(len(context))]
                retrived_command_list = [context[i]['command'] for i in range(len(context))]
                if command in retrived_command_list:
                    correct_count += 1
                    rank = retrived_command_list.index(command) + 1
                    rr_total += 1 / rank

            print(f"Correct: {correct_count/len(commands_list)}, Total: {rr_total/len(commands_list)}")
            scores[k] = correct_count / len(commands_list)
            mrr[k] = rr_total / len(commands_list)

        plt.plot(list(scores.keys()), list(scores.values()), marker='o', label='Recall')
        plt.plot(list(mrr.keys()), list(mrr.values()), marker='^', label='MRR')
        plt.legend()
        plt.xlabel("k")
        plt.ylabel("Score")
        plt.savefig("info_RAG_evaluation.png")
        plt.close()
